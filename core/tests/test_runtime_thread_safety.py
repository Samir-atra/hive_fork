import threading
import time
from pathlib import Path
from framework.runtime.core import Runtime

def test_runtime_thread_isolation(tmp_path: Path):
    runtime = Runtime(tmp_path / "test_storage")

    # Thread 1 function
    def thread1_func():
        runtime.start_run("goal_1", "Thread 1 Goal")
        runtime.set_node("node_1")
        time.sleep(0.1) # Simulate some work, allowing thread 2 to interleave
        assert runtime.current_run.goal_id == "goal_1", f"Expected goal_1, got {runtime.current_run.goal_id}"
        assert getattr(runtime._local, "current_node", None) == "node_1", f"Expected node_1, got {getattr(runtime._local, 'current_node', None)}"
        runtime.end_run(success=True)

    # Thread 2 function
    def thread2_func():
        time.sleep(0.05) # Start slightly after thread 1
        runtime.start_run("goal_2", "Thread 2 Goal")
        runtime.set_node("node_2")
        time.sleep(0.1)
        assert runtime.current_run.goal_id == "goal_2", f"Expected goal_2, got {runtime.current_run.goal_id}"
        assert getattr(runtime._local, "current_node", None) == "node_2", f"Expected node_2, got {getattr(runtime._local, 'current_node', None)}"
        runtime.end_run(success=True)

    t1 = threading.Thread(target=thread1_func)
    t2 = threading.Thread(target=thread2_func)

    t1.start()
    t2.start()

    t1.join()
    t2.join()
