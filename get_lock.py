import asyncio
from core.framework.runtime.shared_state import SharedStateManager

manager = SharedStateManager()
print(manager._key_locks)
