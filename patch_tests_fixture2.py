import re

with open("core/framework/server/tests/test_api.py", "r") as f:
    content = f.read()

content = re.sub(
    r'''        with open\(cp_dir / "cp_node_complete_node_a_001\.json", "w"\) as f:\n            json\.dump\(\n                {\n                    "checkpoint_id": "cp_node_complete_node_a_001",\n                    "current_node": "node_a",\n                    "is_clean": True,\n                    "timestamp": "2026-02-20T12:01:00",\n                },\n                f,\n            \)''',
    '''        with open(cp_dir / "cp_node_complete_node_a_001.json", "w") as f:
            json.dump(
                {
                    "checkpoint_id": "cp_node_complete_node_a_001",
                    "checkpoint_type": "node_complete",
                    "session_id": "session_20260220_120000_abc12345",
                    "created_at": "2026-02-20T12:01:00",
                    "current_node": "node_a",
                    "is_clean": True,
                    "timestamp": "2026-02-20T12:01:00",
                },
                f,
            )''',
    content
)

with open("core/framework/server/tests/test_api.py", "w") as f:
    f.write(content)
