import { useMemo, useCallback } from "react";
import {
  ReactFlow,
  Controls,
  Background,
  MarkerType,
  Position,
  Node as FlowNode,
  Edge as FlowEdge
} from "@xyflow/react";
import dagre from "dagre";
import { CustomNode } from "./CustomNode";
import "@xyflow/react/dist/style.css";

import type { DraftGraph as DraftGraphData } from "@/api/types";
import type { GraphNode } from "@/components/graph-types";

interface GraphVisualizerProps {
  draft?: DraftGraphData | null;
  runtimeNodes?: GraphNode[] | null;
  onNodeClick?: (nodeId: string) => void;
}

const nodeTypes = {
  custom: CustomNode,
};

const getLayoutedElements = (nodes: FlowNode[], edges: FlowEdge[], direction = "TB") => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: direction });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: 200, height: 80 });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      targetPosition: Position.Top,
      sourcePosition: Position.Bottom,
      position: {
        x: nodeWithPosition.x - 100,
        y: nodeWithPosition.y - 40,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
};

export default function GraphVisualizer({ draft, runtimeNodes, onNodeClick }: GraphVisualizerProps) {
  const initialNodes: FlowNode[] = useMemo(() => {
    const rfNodes: FlowNode[] = [];
    if (draft?.nodes) {
      draft.nodes.forEach((dn) => {
        const rn = runtimeNodes?.find((r) => r.id === dn.id);
        const isStart = draft.entry_node === dn.id;
        const isEnd = draft.terminal_nodes?.includes(dn.id);
        rfNodes.push({
          id: dn.id,
          type: 'custom',
          position: { x: 0, y: 0 },
          data: {
            label: dn.name,
            nodeType: isStart ? "start" : isEnd ? "end" : dn.node_type,
            tools: dn.tools,
            status: rn?.status,
          },
        });
      });
    } else if (runtimeNodes) {
      runtimeNodes.forEach((rn) => {
        rfNodes.push({
          id: rn.id,
          type: 'custom',
          position: { x: 0, y: 0 },
          data: {
            label: rn.label,
            nodeType: rn.nodeType || "execution",
            tools: [],
            status: rn.status,
          },
        });
      });
    }
    return rfNodes;
  }, [draft, runtimeNodes]);

  const initialEdges: FlowEdge[] = useMemo(() => {
    const rfEdges: FlowEdge[] = [];
    if (draft?.edges) {
      draft.edges.forEach((de) => {
        rfEdges.push({
          id: de.id,
          source: de.source,
          target: de.target,
          label: de.label || de.condition,
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: '#888',
          },
          style: { stroke: '#888' },
        });
      });
    } else if (runtimeNodes) {
      runtimeNodes.forEach((rn) => {
        if (rn.next) {
          rn.next.forEach((target, idx) => {
            rfEdges.push({
              id: `${rn.id}-${target}-${idx}`,
              source: rn.id,
              target: target,
              markerEnd: {
                type: MarkerType.ArrowClosed,
                color: '#888',
              },
              style: { stroke: '#888' },
            });
          });
        }
      });
    }
    return rfEdges;
  }, [draft, runtimeNodes]);

  const { nodes: layoutedNodes, edges: layoutedEdges } = useMemo(
    () => getLayoutedElements(initialNodes, initialEdges),
    [initialNodes, initialEdges]
  );

  const onNodeClickCallback = useCallback((_: React.MouseEvent, node: FlowNode) => {
    if (onNodeClick) onNodeClick(node.id);
  }, [onNodeClick]);

  return (
    <div style={{ width: '100%', height: '100%' }}>
      <ReactFlow
        nodes={layoutedNodes}
        edges={layoutedEdges}
        nodeTypes={nodeTypes}
        onNodeClick={onNodeClickCallback}
        fitView
      >
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}
