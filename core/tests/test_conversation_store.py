"""Tests for framework.storage.conversation_store.FileConversationStore.

Covers part write/read, metadata persistence, cursor persistence,
partial deletion, full destruction, and edge cases (empty store,
corrupted JSON, missing directories).  All I/O is isolated via the
``tmp_path`` fixture.

Resolves: https://github.com/adenhq/hive/issues/4100
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from framework.storage.conversation_store import FileConversationStore


# ---------------------------------------------------------------------------
# write_part / read_parts
# ---------------------------------------------------------------------------


class TestWriteReadParts:
    """Tests for writing and reading conversation parts."""

    @pytest.mark.asyncio
    async def test_single_part_round_trip(self, tmp_path: Path) -> None:
        """A single part should round-trip correctly."""
        store = FileConversationStore(tmp_path / "conv")
        data = {"role": "user", "content": "hello"}
        await store.write_part(0, data)

        parts = await store.read_parts()
        assert len(parts) == 1
        assert parts[0] == data

    @pytest.mark.asyncio
    async def test_multiple_parts_ordered(self, tmp_path: Path) -> None:
        """Parts should be returned in sequence-number order."""
        store = FileConversationStore(tmp_path / "conv")
        for i in range(5):
            await store.write_part(i, {"seq": i, "content": f"msg-{i}"})

        parts = await store.read_parts()
        assert len(parts) == 5
        for i, part in enumerate(parts):
            assert part["seq"] == i

    @pytest.mark.asyncio
    async def test_read_empty_store(self, tmp_path: Path) -> None:
        """Reading from a store with no parts should return an empty list."""
        store = FileConversationStore(tmp_path / "empty")
        assert await store.read_parts() == []

    @pytest.mark.asyncio
    async def test_part_file_naming(self, tmp_path: Path) -> None:
        """Part files should be zero-padded 10-digit names."""
        store = FileConversationStore(tmp_path / "conv")
        await store.write_part(42, {"data": "x"})

        expected = tmp_path / "conv" / "parts" / "0000000042.json"
        assert expected.exists()

    @pytest.mark.asyncio
    async def test_overwrite_existing_part(self, tmp_path: Path) -> None:
        """Writing to the same sequence number should overwrite."""
        store = FileConversationStore(tmp_path / "conv")
        await store.write_part(0, {"version": 1})
        await store.write_part(0, {"version": 2})

        parts = await store.read_parts()
        assert len(parts) == 1
        assert parts[0]["version"] == 2

    @pytest.mark.asyncio
    async def test_skips_corrupted_part(self, tmp_path: Path) -> None:
        """Corrupted part files should be silently skipped."""
        store = FileConversationStore(tmp_path / "conv")
        await store.write_part(0, {"good": True})

        # Manually corrupt a part file
        bad_file = tmp_path / "conv" / "parts" / "0000000001.json"
        bad_file.parent.mkdir(parents=True, exist_ok=True)
        bad_file.write_text("{broken json!!")

        parts = await store.read_parts()
        assert len(parts) == 1
        assert parts[0]["good"] is True


# ---------------------------------------------------------------------------
# write_meta / read_meta
# ---------------------------------------------------------------------------


class TestMetaPersistence:
    """Tests for conversation metadata."""

    @pytest.mark.asyncio
    async def test_meta_round_trip(self, tmp_path: Path) -> None:
        """Metadata should round-trip correctly."""
        store = FileConversationStore(tmp_path / "conv")
        meta = {"node_id": "search", "model": "gpt-4o", "tokens": 150}
        await store.write_meta(meta)

        loaded = await store.read_meta()
        assert loaded == meta

    @pytest.mark.asyncio
    async def test_read_meta_missing(self, tmp_path: Path) -> None:
        """Reading metadata from a fresh store should return None."""
        store = FileConversationStore(tmp_path / "conv")
        assert await store.read_meta() is None

    @pytest.mark.asyncio
    async def test_meta_overwrite(self, tmp_path: Path) -> None:
        """Writing metadata twice should overwrite."""
        store = FileConversationStore(tmp_path / "conv")
        await store.write_meta({"version": 1})
        await store.write_meta({"version": 2})

        loaded = await store.read_meta()
        assert loaded["version"] == 2

    @pytest.mark.asyncio
    async def test_meta_file_location(self, tmp_path: Path) -> None:
        """Meta should be stored as meta.json in the base directory."""
        store = FileConversationStore(tmp_path / "conv")
        await store.write_meta({"k": "v"})

        meta_file = tmp_path / "conv" / "meta.json"
        assert meta_file.exists()
        data = json.loads(meta_file.read_text())
        assert data["k"] == "v"

    @pytest.mark.asyncio
    async def test_read_corrupted_meta(self, tmp_path: Path) -> None:
        """Corrupted meta.json should return None."""
        base = tmp_path / "conv"
        base.mkdir(parents=True)
        (base / "meta.json").write_text("not-json{{")

        store = FileConversationStore(base)
        assert await store.read_meta() is None


# ---------------------------------------------------------------------------
# write_cursor / read_cursor
# ---------------------------------------------------------------------------


class TestCursorPersistence:
    """Tests for cursor state."""

    @pytest.mark.asyncio
    async def test_cursor_round_trip(self, tmp_path: Path) -> None:
        """Cursor data should round-trip correctly."""
        store = FileConversationStore(tmp_path / "conv")
        cursor = {"position": 42, "node": "output"}
        await store.write_cursor(cursor)

        loaded = await store.read_cursor()
        assert loaded == cursor

    @pytest.mark.asyncio
    async def test_read_cursor_missing(self, tmp_path: Path) -> None:
        """Reading cursor from a fresh store should return None."""
        store = FileConversationStore(tmp_path / "conv")
        assert await store.read_cursor() is None

    @pytest.mark.asyncio
    async def test_cursor_file_location(self, tmp_path: Path) -> None:
        """Cursor should be stored as cursor.json in the base directory."""
        store = FileConversationStore(tmp_path / "conv")
        await store.write_cursor({"pos": 0})

        cursor_file = tmp_path / "conv" / "cursor.json"
        assert cursor_file.exists()

    @pytest.mark.asyncio
    async def test_read_corrupted_cursor(self, tmp_path: Path) -> None:
        """Corrupted cursor.json should return None."""
        base = tmp_path / "conv"
        base.mkdir(parents=True)
        (base / "cursor.json").write_text("}}bad")

        store = FileConversationStore(base)
        assert await store.read_cursor() is None


# ---------------------------------------------------------------------------
# delete_parts_before
# ---------------------------------------------------------------------------


class TestDeletePartsBefore:
    """Tests for partial cleanup of old parts."""

    @pytest.mark.asyncio
    async def test_deletes_earlier_parts(self, tmp_path: Path) -> None:
        """Parts with seq < threshold should be removed."""
        store = FileConversationStore(tmp_path / "conv")
        for i in range(5):
            await store.write_part(i, {"seq": i})

        await store.delete_parts_before(3)

        parts = await store.read_parts()
        assert len(parts) == 2
        seqs = [p["seq"] for p in parts]
        assert seqs == [3, 4]

    @pytest.mark.asyncio
    async def test_delete_all_before_first(self, tmp_path: Path) -> None:
        """Deleting before seq 0 should be a no-op."""
        store = FileConversationStore(tmp_path / "conv")
        await store.write_part(0, {"seq": 0})
        await store.write_part(1, {"seq": 1})

        await store.delete_parts_before(0)

        parts = await store.read_parts()
        assert len(parts) == 2

    @pytest.mark.asyncio
    async def test_delete_on_empty_store(self, tmp_path: Path) -> None:
        """Deleting from an empty store should not raise."""
        store = FileConversationStore(tmp_path / "conv")
        await store.delete_parts_before(10)  # Should not raise

    @pytest.mark.asyncio
    async def test_delete_preserves_meta_and_cursor(
        self, tmp_path: Path
    ) -> None:
        """delete_parts_before should not affect meta or cursor files."""
        store = FileConversationStore(tmp_path / "conv")
        await store.write_part(0, {"seq": 0})
        await store.write_meta({"node": "x"})
        await store.write_cursor({"pos": 5})

        await store.delete_parts_before(1)

        assert await store.read_meta() == {"node": "x"}
        assert await store.read_cursor() == {"pos": 5}


# ---------------------------------------------------------------------------
# destroy
# ---------------------------------------------------------------------------


class TestDestroy:
    """Tests for full cleanup (destroy)."""

    @pytest.mark.asyncio
    async def test_destroy_removes_everything(self, tmp_path: Path) -> None:
        """destroy() should remove the entire base directory."""
        base = tmp_path / "conv"
        store = FileConversationStore(base)
        await store.write_part(0, {"data": "x"})
        await store.write_meta({"m": 1})
        await store.write_cursor({"c": 2})

        await store.destroy()

        assert not base.exists()

    @pytest.mark.asyncio
    async def test_destroy_nonexistent_dir(self, tmp_path: Path) -> None:
        """destroy() on a non-existent directory should not raise."""
        store = FileConversationStore(tmp_path / "ghost")
        await store.destroy()  # Should not raise

    @pytest.mark.asyncio
    async def test_read_after_destroy(self, tmp_path: Path) -> None:
        """Reads after destroy should return empty/None values."""
        base = tmp_path / "conv"
        store = FileConversationStore(base)
        await store.write_part(0, {"data": "x"})
        await store.destroy()

        assert await store.read_parts() == []
        assert await store.read_meta() is None
        assert await store.read_cursor() is None


# ---------------------------------------------------------------------------
# close (no-op)
# ---------------------------------------------------------------------------


class TestClose:
    """Tests for the close() method."""

    @pytest.mark.asyncio
    async def test_close_is_noop(self, tmp_path: Path) -> None:
        """close() should complete without error and not affect data."""
        store = FileConversationStore(tmp_path / "conv")
        await store.write_part(0, {"data": "x"})
        await store.close()

        # Data should still be readable
        parts = await store.read_parts()
        assert len(parts) == 1
