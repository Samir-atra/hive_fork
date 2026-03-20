import re

with open("core/framework/server/routes_sessions.py", "r") as f:
    content = f.read()

content = content.replace(
    '''            checkpoints.append(
                {
                    "checkpoint_id": f.stem,
                    "current_node": data.get("current_node"),
                    "next_node": data.get("next_node"),
                    "is_clean": data.get("is_clean", False),
                    "timestamp": data.get("timestamp"),
                }
            )''',
    '''            checkpoints.append(
                {
                    "checkpoint_id": f.stem,
                    "current_node": data.get("current_node"),
                    "next_node": data.get("next_node"),
                    "is_clean": data.get("is_clean", False),
                    "is_starred": data.get("is_starred", False),
                    "timestamp": data.get("timestamp"),
                }
            )'''
)

star_method = '''
async def handle_star_checkpoint(request: web.Request) -> web.Response:
    """Star/unstar a checkpoint."""
    session, err = resolve_session(request)
    if err:
        return err

    if not session.worker_path:
        return web.json_response({"error": "No worker loaded"}, status=503)

    ws_id = request.match_info.get("ws_id") or request.match_info.get("session_id", "")
    ws_id = safe_path_segment(ws_id)
    checkpoint_id = safe_path_segment(request.match_info["checkpoint_id"])

    try:
        body = await request.json()
        is_starred = bool(body.get("is_starred", False))
    except Exception:
        return web.json_response({"error": "Invalid JSON body"}, status=400)

    from framework.storage.checkpoint_store import CheckpointStore
    store = CheckpointStore(sessions_dir(session) / ws_id)
    updated = await store.update_checkpoint_star(checkpoint_id, is_starred)

    if not updated:
        return web.json_response({"error": "Checkpoint not found or failed to update"}, status=404)

    return web.json_response({"success": True})
'''

content = content.replace(
    'async def handle_delete_worker_session(request: web.Request) -> web.Response:',
    f'{star_method}\n\nasync def handle_delete_worker_session(request: web.Request) -> web.Response:'
)

content = content.replace(
    '''    app.router.add_post(
        "/api/sessions/{session_id}/worker-sessions/{ws_id}/checkpoints/{checkpoint_id}/restore",
        handle_restore_checkpoint,
    )''',
    '''    app.router.add_post(
        "/api/sessions/{session_id}/worker-sessions/{ws_id}/checkpoints/{checkpoint_id}/restore",
        handle_restore_checkpoint,
    )
    app.router.add_put(
        "/api/sessions/{session_id}/worker-sessions/{ws_id}/checkpoints/{checkpoint_id}/star",
        handle_star_checkpoint,
    )'''
)

with open("core/framework/server/routes_sessions.py", "w") as f:
    f.write(content)
