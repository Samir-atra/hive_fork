import re

with open("core/framework/server/tests/test_api.py", "r") as f:
    content = f.read()

test_star = '''
    @pytest.mark.asyncio
    async def test_star_checkpoint(self, sample_session, tmp_agent_dir):
        session_id, session_dir, state = sample_session
        tmp_path, agent_name, base = tmp_agent_dir

        session = _make_session(tmp_dir=tmp_path / ".hive" / "agents" / agent_name)
        app = _make_app_with_session(session)

        async with TestClient(TestServer(app)) as client:
            resp = await client.put(
                f"/api/sessions/test_agent/worker-sessions/{session_id}/checkpoints/cp_node_complete_node_a_001/star",
                json={"is_starred": True}
            )
            assert resp.status == 200
            data = await resp.json()
            assert data["success"] is True

            # Verify it is starred in the list
            resp = await client.get(
                f"/api/sessions/test_agent/worker-sessions/{session_id}/checkpoints"
            )
            data = await resp.json()
            cp = data["checkpoints"][0]
            assert cp["is_starred"] is True
'''

content = content.replace(
    'class TestMessages:',
    f'{test_star}\n\nclass TestMessages:'
)

with open("core/framework/server/tests/test_api.py", "w") as f:
    f.write(content)
