with open("core/framework/server/tests/test_api.py", "r") as f:
    content = f.read()

content = content.replace(
    '''    cp_data = {
        "checkpoint_id": "cp_node_complete_node_a_001",
        "current_node": "node_a",
        "next_node": "node_b",
        "is_clean": True,
        "timestamp": "2026-02-20T12:01:00",
    }''',
    '''    cp_data = {
        "checkpoint_id": "cp_node_complete_node_a_001",
        "checkpoint_type": "node_complete",
        "session_id": "session_20260220_120000_abc12345",
        "created_at": "2026-02-20T12:01:00",
        "current_node": "node_a",
        "next_node": "node_b",
        "is_clean": True,
        "timestamp": "2026-02-20T12:01:00",
    }'''
)

with open("core/framework/server/tests/test_api.py", "w") as f:
    f.write(content)
