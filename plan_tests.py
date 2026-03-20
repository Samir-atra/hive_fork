import pytest
from core.framework.runtime.shared_state import SharedStateManager, StreamMemory, IsolationLevel

manager = SharedStateManager()
memory = StreamMemory(manager, "exec_1", "stream_1", IsolationLevel.SYNCHRONIZED)

def test_sync():
    memory.write_sync("foo", "bar")
    assert memory.read_sync("foo") == "bar"
    assert memory.read_all_sync() == {"foo": "bar"}

test_sync()
print("Success")
