with open("core/framework/storage/checkpoint_store.py", "r") as f:
    content = f.read()

# Add logic to skip pruning if is_starred
content = content.replace(
    '''        for cp in index.checkpoints:
            try:
                created = datetime.fromisoformat(cp.created_at)
                if created < cutoff:
                    old_checkpoints.append(cp.checkpoint_id)
            except Exception as e:''',
    '''        for cp in index.checkpoints:
            if getattr(cp, "is_starred", False):
                continue
            try:
                created = datetime.fromisoformat(cp.created_at)
                if created < cutoff:
                    old_checkpoints.append(cp.checkpoint_id)
            except Exception as e:'''
)

update_method = '''
    async def update_checkpoint_star(self, checkpoint_id: str, is_starred: bool) -> bool:
        """
        Update the is_starred status of a checkpoint.

        Args:
            checkpoint_id: Checkpoint ID
            is_starred: True to star, False to unstar

        Returns:
            True if updated, False if not found
        """

        def _update(checkpoint_id: str, is_starred: bool) -> bool:
            checkpoint_path = self.checkpoints_dir / f"{checkpoint_id}.json"
            if not checkpoint_path.exists():
                return False

            try:
                # Load, update, save
                cp = Checkpoint.model_validate_json(checkpoint_path.read_text(encoding="utf-8"))
                cp.is_starred = is_starred
                with atomic_write(checkpoint_path) as f:
                    f.write(cp.model_dump_json(indent=2))
                return True
            except Exception as e:
                logger.error(f"Failed to update checkpoint star status {checkpoint_id}: {e}")
                return False

        updated = await asyncio.to_thread(_update, checkpoint_id, is_starred)
        if updated:
            async with self._index_lock:
                await self._update_index_star(checkpoint_id, is_starred)

        return updated

    async def _update_index_star(self, checkpoint_id: str, is_starred: bool) -> None:
        """Update index after starring a checkpoint."""

        def _write(index: CheckpointIndex):
            with atomic_write(self.index_path) as f:
                f.write(index.model_dump_json(indent=2))

        index = await self.load_index()
        if not index:
            return

        for cp in index.checkpoints:
            if cp.checkpoint_id == checkpoint_id:
                cp.is_starred = is_starred
                break

        await asyncio.to_thread(_write, index)
'''

content = content.replace(
    'async def _update_index_add(self, checkpoint: Checkpoint) -> None:',
    f'{update_method}\n    async def _update_index_add(self, checkpoint: Checkpoint) -> None:'
)

with open("core/framework/storage/checkpoint_store.py", "w") as f:
    f.write(content)
