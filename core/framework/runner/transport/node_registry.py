"""Node Registry for distributed agent discovery and health monitoring.

Provides local registry for node discovery within a cluster, node health
monitoring via heartbeat, and capability advertisement.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from framework.runner.protocol import CapabilityLevel, CapabilityResponse
from framework.runner.transport.transport import (
    NodeInfo,
    TransportConfig,
)

if TYPE_CHECKING:
    from framework.runner.transport.transport import Transport

logger = logging.getLogger(__name__)


class NodeStatus:
    """Status of a registered node."""

    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"


@dataclass
class RegisteredNode:
    """A node registered with the registry."""

    info: NodeInfo
    transport: Any = None
    last_heartbeat: float = field(default_factory=time.time)
    failed_health_checks: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class NodeRegistry:
    """Registry for discovering and managing remote nodes.

    Features:
    - Node registration and discovery
    - Health monitoring via heartbeat
    - Capability-based lookup
    - Automatic failover detection

    Usage:
        registry = NodeRegistry()

        # Register a remote node
        await registry.register_node(NodeInfo(
            node_id="gpu-server-1",
            address=NodeAddress(url="ws://gpu-server:8080"),
            name="GPU Server 1",
            capabilities=["image_processing", "ml_inference"],
        ))

        # Find nodes by capability
        nodes = await registry.find_by_capability("ml_inference")

        # Get healthy nodes
        healthy = await registry.get_healthy_nodes()
    """

    def __init__(
        self,
        config: TransportConfig | None = None,
        heartbeat_timeout: float = 60.0,
        health_check_interval: float = 30.0,
        max_failed_checks: int = 3,
    ):
        self._config = config or TransportConfig()
        self._heartbeat_timeout = heartbeat_timeout
        self._health_check_interval = health_check_interval
        self._max_failed_checks = max_failed_checks

        self._nodes: dict[str, RegisteredNode] = {}
        self._capability_index: dict[str, set[str]] = {}
        self._local_node_id: str | None = None
        self._health_task: asyncio.Task | None = None
        self._on_node_status_change: Callable[[str, str], None] | None = None

    @property
    def local_node_id(self) -> str | None:
        return self._local_node_id

    @local_node_id.setter
    def local_node_id(self, value: str) -> None:
        self._local_node_id = value

    def set_status_callback(self, callback: Callable[[str, str], None]) -> None:
        """Set callback for node status changes.

        Args:
            callback: Function called with (node_id, new_status)
        """
        self._on_node_status_change = callback

    async def start(self) -> None:
        """Start the registry health monitoring."""
        if self._health_task is None:
            self._health_task = asyncio.create_task(self._health_check_loop())
            logger.info("Node registry started")

    async def stop(self) -> None:
        """Stop the registry and disconnect all nodes."""
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
            self._health_task = None

        for node in self._nodes.values():
            if node.transport:
                await node.transport.disconnect()

        self._nodes.clear()
        self._capability_index.clear()
        logger.info("Node registry stopped")

    async def register_node(
        self,
        info: NodeInfo,
        transport: Transport | None = None,
    ) -> None:
        """Register a new node with the registry.

        Args:
            info: Node information
            transport: Optional transport for the node
        """
        node_id = info.node_id

        if node_id in self._nodes:
            logger.warning(f"Node {node_id} already registered, updating")
            self._nodes[node_id].info = info
            if transport:
                self._nodes[node_id].transport = transport
        else:
            self._nodes[node_id] = RegisteredNode(
                info=info,
                transport=transport,
                last_heartbeat=time.time(),
            )
            logger.info(f"Registered node: {node_id} at {info.address}")

        for cap in info.capabilities:
            if cap not in self._capability_index:
                self._capability_index[cap] = set()
            self._capability_index[cap].add(node_id)

    async def unregister_node(self, node_id: str) -> bool:
        """Unregister a node from the registry.

        Args:
            node_id: ID of the node to unregister

        Returns:
            True if node was unregistered, False if not found
        """
        if node_id not in self._nodes:
            return False

        node = self._nodes.pop(node_id)

        for cap in node.info.capabilities:
            if cap in self._capability_index:
                self._capability_index[cap].discard(node_id)
                if not self._capability_index[cap]:
                    del self._capability_index[cap]

        if node.transport:
            await node.transport.disconnect()

        logger.info(f"Unregistered node: {node_id}")
        return True

    async def record_heartbeat(self, node_id: str) -> bool:
        """Record a heartbeat from a node.

        Args:
            node_id: ID of the node sending heartbeat

        Returns:
            True if heartbeat recorded, False if node not found
        """
        if node_id not in self._nodes:
            return False

        node = self._nodes[node_id]
        node.last_heartbeat = time.time()
        node.failed_health_checks = 0

        if node.info.status != NodeStatus.HEALTHY:
            node.info.status = NodeStatus.HEALTHY
            if self._on_node_status_change:
                self._on_node_status_change(node_id, NodeStatus.HEALTHY)

        return True

    async def find_by_capability(self, capability: str) -> list[NodeInfo]:
        """Find nodes that have a specific capability.

        Args:
            capability: The capability to search for

        Returns:
            List of nodes with the capability
        """
        node_ids = self._capability_index.get(capability, set())
        return [self._nodes[nid].info for nid in node_ids if nid in self._nodes]

    async def find_by_capabilities(
        self,
        capabilities: list[str],
        match_all: bool = False,
    ) -> list[NodeInfo]:
        """Find nodes by multiple capabilities.

        Args:
            capabilities: List of capabilities to search for
            match_all: If True, node must have all capabilities

        Returns:
            List of matching nodes
        """
        if not capabilities:
            return []

        result_sets = []
        for cap in capabilities:
            node_ids = self._capability_index.get(cap, set())
            result_sets.append(node_ids)

        if match_all:
            matching_ids = set.intersection(*result_sets)
        else:
            matching_ids = set.union(*result_sets)

        return [self._nodes[nid].info for nid in matching_ids if nid in self._nodes]

    async def get_node(self, node_id: str) -> NodeInfo | None:
        """Get a specific node by ID.

        Args:
            node_id: The node ID

        Returns:
            NodeInfo if found, None otherwise
        """
        node = self._nodes.get(node_id)
        return node.info if node else None

    async def get_healthy_nodes(self) -> list[NodeInfo]:
        """Get all healthy nodes.

        Returns:
            List of healthy nodes
        """
        return [
            node.info for node in self._nodes.values() if node.info.status == NodeStatus.HEALTHY
        ]

    async def get_all_nodes(self) -> list[NodeInfo]:
        """Get all registered nodes.

        Returns:
            List of all nodes
        """
        return [node.info for node in self._nodes.values()]

    def get_node_transport(self, node_id: str) -> Any:
        """Get the transport for a node.

        Args:
            node_id: The node ID

        Returns:
            Transport if available, None otherwise
        """
        node = self._nodes.get(node_id)
        return node.transport if node else None

    async def get_capability_response(
        self,
        node_id: str,
    ) -> CapabilityResponse | None:
        """Get a CapabilityResponse for a node.

        This is used for integration with the AgentOrchestrator routing.

        Args:
            node_id: The node ID

        Returns:
            CapabilityResponse if node found, None otherwise
        """
        node = self._nodes.get(node_id)
        if not node:
            return None

        level = CapabilityLevel.CAN_HANDLE
        if node.info.status == NodeStatus.HEALTHY:
            level = CapabilityLevel.BEST_FIT
        elif node.info.status == NodeStatus.UNHEALTHY:
            level = CapabilityLevel.UNCERTAIN
        elif node.info.status == NodeStatus.OFFLINE:
            level = CapabilityLevel.CANNOT_HANDLE

        return CapabilityResponse(
            agent_name=node_id,
            level=level,
            confidence=1.0 if node.info.status == NodeStatus.HEALTHY else 0.5,
            reasoning=f"Remote node with capabilities: {', '.join(node.info.capabilities)}",
            dependencies=[],
        )

    async def _health_check_loop(self) -> None:
        """Background task to check node health."""
        while True:
            try:
                await asyncio.sleep(self._health_check_interval)
                await self._check_all_nodes()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")

    async def _check_all_nodes(self) -> None:
        """Check health of all registered nodes."""
        now = time.time()

        for node_id, node in list(self._nodes.items()):
            if node_id == self._local_node_id:
                continue

            time_since_heartbeat = now - node.last_heartbeat

            if time_since_heartbeat > self._heartbeat_timeout:
                node.failed_health_checks += 1

                if node.failed_health_checks >= self._max_failed_checks:
                    new_status = NodeStatus.OFFLINE
                else:
                    new_status = NodeStatus.UNHEALTHY

                if node.info.status != new_status:
                    node.info.status = new_status
                    logger.warning(
                        f"Node {node_id} status: {new_status} "
                        f"(last heartbeat: {time_since_heartbeat:.1f}s ago)"
                    )
                    if self._on_node_status_change:
                        self._on_node_status_change(node_id, new_status)
            elif node.info.status != NodeStatus.HEALTHY:
                node.info.status = NodeStatus.HEALTHY
                if self._on_node_status_change:
                    self._on_node_status_change(node_id, NodeStatus.HEALTHY)

    def get_stats(self) -> dict[str, Any]:
        """Get registry statistics.

        Returns:
            Dictionary with stats
        """
        status_counts = {}
        for node in self._nodes.values():
            status = node.info.status
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_nodes": len(self._nodes),
            "capabilities": list(self._capability_index.keys()),
            "status_counts": status_counts,
        }
