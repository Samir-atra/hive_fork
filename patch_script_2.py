with open("core/framework/storage/checkpoint_store.py", "r") as f:
    content = f.read()

content = content.replace(
    '''    async def list_checkpoints(
        self,
        checkpoint_type: str | None = None,
        is_clean: bool | None = None,
    ) -> list[CheckpointSummary]:''',
    '''    async def list_checkpoints(
        self,
        checkpoint_type: str | None = None,
        is_clean: bool | None = None,
        is_starred: bool | None = None,
    ) -> list[CheckpointSummary]:'''
)

content = content.replace(
    '''        if is_clean is not None:
            checkpoints = [cp for cp in checkpoints if cp.is_clean == is_clean]

        return checkpoints''',
    '''        if is_clean is not None:
            checkpoints = [cp for cp in checkpoints if cp.is_clean == is_clean]

        if is_starred is not None:
            checkpoints = [cp for cp in checkpoints if getattr(cp, "is_starred", False) == is_starred]

        return checkpoints'''
)

with open("core/framework/storage/checkpoint_store.py", "w") as f:
    f.write(content)
