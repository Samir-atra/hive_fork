"""
Tests for the agent generation prompts module.

Verifies that:
1. All prompts are exported correctly
2. Prompts contain required schema information
3. Examples in prompts are valid JSON
"""

import json
import re

import pytest


class TestPromptExports:
    """Test that prompts are properly exported."""

    def test_import_from_main_module(self):
        """Test importing from framework.prompts"""
        from framework.prompts import (
            AGENT_GENERATION_COMPACT_PROMPT,
            AGENT_GENERATION_SYSTEM_PROMPT,
            AGENT_JSON_SCHEMA,
        )

        assert AGENT_JSON_SCHEMA is not None
        assert AGENT_GENERATION_SYSTEM_PROMPT is not None
        assert AGENT_GENERATION_COMPACT_PROMPT is not None

    def test_import_from_submodule(self):
        """Test importing from framework.prompts.agent_schema"""
        from framework.prompts.agent_schema import (
            AGENT_GENERATION_COMPACT_PROMPT,
            AGENT_GENERATION_SYSTEM_PROMPT,
            AGENT_JSON_SCHEMA,
        )

        assert isinstance(AGENT_JSON_SCHEMA, str)
        assert isinstance(AGENT_GENERATION_SYSTEM_PROMPT, str)
        assert isinstance(AGENT_GENERATION_COMPACT_PROMPT, str)

    def test_all_exports_are_strings(self):
        """All prompts should be strings."""
        from framework.prompts import (
            AGENT_GENERATION_COMPACT_PROMPT,
            AGENT_GENERATION_SYSTEM_PROMPT,
            AGENT_JSON_SCHEMA,
        )

        assert isinstance(AGENT_JSON_SCHEMA, str)
        assert isinstance(AGENT_GENERATION_SYSTEM_PROMPT, str)
        assert isinstance(AGENT_GENERATION_COMPACT_PROMPT, str)

    def test_prompts_are_not_empty(self):
        """All prompts should have content."""
        from framework.prompts import (
            AGENT_GENERATION_COMPACT_PROMPT,
            AGENT_GENERATION_SYSTEM_PROMPT,
            AGENT_JSON_SCHEMA,
        )

        assert len(AGENT_JSON_SCHEMA) > 100
        assert len(AGENT_GENERATION_SYSTEM_PROMPT) > 100
        assert len(AGENT_GENERATION_COMPACT_PROMPT) > 50


class TestSchemaContent:
    """Test that schema contains required information."""

    def test_schema_contains_node_types(self):
        """Schema should document valid node types."""
        from framework.prompts import AGENT_JSON_SCHEMA

        assert "event_loop" in AGENT_JSON_SCHEMA
        assert "router" in AGENT_JSON_SCHEMA

    def test_schema_contains_edge_conditions(self):
        """Schema should document valid edge conditions."""
        from framework.prompts import AGENT_JSON_SCHEMA

        assert "on_success" in AGENT_JSON_SCHEMA
        assert "on_failure" in AGENT_JSON_SCHEMA
        assert "conditional" in AGENT_JSON_SCHEMA
        assert "always" in AGENT_JSON_SCHEMA

    def test_schema_mentions_critical_rules(self):
        """Schema should mention critical rules like no null targets."""
        from framework.prompts import AGENT_JSON_SCHEMA

        assert "null" in AGENT_JSON_SCHEMA.lower()
        assert "target" in AGENT_JSON_SCHEMA.lower()

    def test_schema_contains_goal_structure(self):
        """Schema should document goal structure."""
        from framework.prompts import AGENT_JSON_SCHEMA

        assert "success_criteria" in AGENT_JSON_SCHEMA
        assert "constraints" in AGENT_JSON_SCHEMA
        assert "goal" in AGENT_JSON_SCHEMA

    def test_system_prompt_contains_examples(self):
        """System prompt should contain JSON examples."""
        from framework.prompts import AGENT_GENERATION_SYSTEM_PROMPT

        assert "```json" in AGENT_GENERATION_SYSTEM_PROMPT
        assert '"agent"' in AGENT_GENERATION_SYSTEM_PROMPT
        assert '"graph"' in AGENT_GENERATION_SYSTEM_PROMPT
        assert '"goal"' in AGENT_GENERATION_SYSTEM_PROMPT

    def test_system_prompt_mentions_node_types(self):
        """System prompt should mention valid node types."""
        from framework.prompts import AGENT_GENERATION_SYSTEM_PROMPT

        assert "event_loop" in AGENT_GENERATION_SYSTEM_PROMPT
        assert "router" in AGENT_GENERATION_SYSTEM_PROMPT

    def test_system_prompt_mentions_edge_conditions(self):
        """System prompt should mention edge conditions."""
        from framework.prompts import AGENT_GENERATION_SYSTEM_PROMPT

        assert "on_success" in AGENT_GENERATION_SYSTEM_PROMPT
        assert "on_failure" in AGENT_GENERATION_SYSTEM_PROMPT
        assert "conditional" in AGENT_GENERATION_SYSTEM_PROMPT

    def test_compact_prompt_is_shorter(self):
        """Compact prompt should be more token-efficient."""
        from framework.prompts import (
            AGENT_GENERATION_COMPACT_PROMPT,
            AGENT_GENERATION_SYSTEM_PROMPT,
        )

        assert len(AGENT_GENERATION_COMPACT_PROMPT) < len(AGENT_GENERATION_SYSTEM_PROMPT)

    def test_compact_prompt_contains_essential_info(self):
        """Compact prompt should contain essential schema info."""
        from framework.prompts import AGENT_GENERATION_COMPACT_PROMPT

        assert "event_loop" in AGENT_GENERATION_COMPACT_PROMPT
        assert "router" in AGENT_GENERATION_COMPACT_PROMPT
        assert "NEVER null" in AGENT_GENERATION_COMPACT_PROMPT


class TestExampleValidity:
    """Test that JSON examples in prompts are valid."""

    def extract_json_blocks(self, text: str) -> list[str]:
        """Extract all JSON code blocks from markdown text."""
        pattern = r"```json\s*(.*?)\s*```"
        matches = re.findall(pattern, text, re.DOTALL)
        return matches

    def is_template_block(self, block: str) -> bool:
        """Check if a JSON block is a template with placeholders."""
        template_indicators = [
            "...",
            "{ ... }",
            "[...]",
            "//",
            "string (",
            "required)",
            "optional)",
        ]
        return any(indicator in block for indicator in template_indicators)

    def test_system_prompt_examples_are_valid_json(self):
        """All complete JSON examples in system prompt should be valid."""
        from framework.prompts import AGENT_GENERATION_SYSTEM_PROMPT

        json_blocks = self.extract_json_blocks(AGENT_GENERATION_SYSTEM_PROMPT)
        assert len(json_blocks) >= 3, "Should have at least 3 JSON examples"

        complete_examples = 0
        for i, block in enumerate(json_blocks):
            if self.is_template_block(block):
                continue
            complete_examples += 1
            try:
                json.loads(block)
            except json.JSONDecodeError as e:
                pytest.fail(f"JSON example {i + 1} is invalid: {e}\nBlock:\n{block[:500]}")

        assert complete_examples >= 3, "Should have at least 3 complete JSON examples"

    def test_schema_json_templates_contain_valid_structure(self):
        """Schema JSON blocks should contain valid structure (allowing placeholders)."""
        from framework.prompts import AGENT_JSON_SCHEMA

        json_blocks = self.extract_json_blocks(AGENT_JSON_SCHEMA)
        assert len(json_blocks) >= 5, "Schema should have multiple JSON structure examples"

        for i, block in enumerate(json_blocks):
            assert "{" in block, f"Block {i + 1} should contain JSON object start"
            assert "}" in block, f"Block {i + 1} should contain JSON object end"

    def test_example_agents_have_required_fields(self):
        """Example agents should have required top-level fields."""
        from framework.prompts import AGENT_GENERATION_SYSTEM_PROMPT

        json_blocks = self.extract_json_blocks(AGENT_GENERATION_SYSTEM_PROMPT)

        complete_agents = []
        for block in json_blocks:
            try:
                data = json.loads(block)
                if "agent" in data and "graph" in data and "goal" in data:
                    complete_agents.append(data)
            except json.JSONDecodeError:
                pass

        assert len(complete_agents) >= 2, "Should have at least 2 complete agent examples"

        for agent in complete_agents:
            assert "id" in agent["agent"], "Agent should have id"
            assert "name" in agent["agent"], "Agent should have name"
            assert "entry_node" in agent["graph"], "Graph should have entry_node"
            assert "nodes" in agent["graph"], "Graph should have nodes"
            assert "edges" in agent["graph"], "Graph should have edges"

    def test_example_nodes_have_required_fields(self):
        """Example nodes should have required fields."""
        from framework.prompts import AGENT_GENERATION_SYSTEM_PROMPT

        json_blocks = self.extract_json_blocks(AGENT_GENERATION_SYSTEM_PROMPT)

        for block in json_blocks:
            try:
                data = json.loads(block)
                if "graph" in data and "nodes" in data.get("graph", {}):
                    for node in data["graph"]["nodes"]:
                        assert "id" in node, f"Node missing id: {node}"
                        assert "name" in node, f"Node missing name: {node}"
                        assert "node_type" in node, f"Node missing node_type: {node}"
            except json.JSONDecodeError:
                pass

    def test_example_edges_have_valid_targets(self):
        """Example edges should never have null targets."""
        from framework.prompts import AGENT_GENERATION_SYSTEM_PROMPT

        json_blocks = self.extract_json_blocks(AGENT_GENERATION_SYSTEM_PROMPT)

        for block in json_blocks:
            try:
                data = json.loads(block)
                if "graph" in data and "edges" in data.get("graph", {}):
                    for edge in data["graph"]["edges"]:
                        assert edge.get("target") is not None, f"Edge has null target: {edge}"
                        assert edge.get("target") != "", f"Edge has empty target: {edge}"
            except json.JSONDecodeError:
                pass

    def test_example_booleans_are_not_strings(self):
        """Example booleans should be true/false, not 'true'/'false'."""
        from framework.prompts import AGENT_GENERATION_SYSTEM_PROMPT

        json_blocks = self.extract_json_blocks(AGENT_GENERATION_SYSTEM_PROMPT)

        for block in json_blocks:
            try:
                data = json.loads(block)
                if "graph" in data and "nodes" in data.get("graph", {}):
                    for node in data["graph"]["nodes"]:
                        if "client_facing" in node:
                            cf = node["client_facing"]
                            assert isinstance(cf, bool), (
                                f"client_facing should be bool, got {type(cf)}: {cf}"
                            )
            except json.JSONDecodeError:
                pass


class TestPromptUsagePatterns:
    """Test expected usage patterns for the prompts."""

    def test_can_use_in_system_message(self):
        """Prompts should be usable as LLM system messages."""
        from framework.prompts import AGENT_GENERATION_SYSTEM_PROMPT

        messages = [
            {"role": "system", "content": AGENT_GENERATION_SYSTEM_PROMPT},
            {"role": "user", "content": "Create a research agent"},
        ]

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert len(messages[0]["content"]) > 0

    def test_can_combine_prompts(self):
        """Prompts should be combinable for context."""
        from framework.prompts import (
            AGENT_GENERATION_COMPACT_PROMPT,
            AGENT_JSON_SCHEMA,
        )

        combined = f"{AGENT_GENERATION_COMPACT_PROMPT}\n\n{AGENT_JSON_SCHEMA}"
        assert "event_loop" in combined
        assert "router" in combined

    def test_compact_prompt_for_token_limits(self):
        """Compact prompt should fit within typical context limits."""
        from framework.prompts import AGENT_GENERATION_COMPACT_PROMPT

        token_estimate = len(AGENT_GENERATION_COMPACT_PROMPT) // 4
        assert token_estimate < 2000, f"Compact prompt too long: ~{token_estimate} tokens"
