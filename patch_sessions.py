with open("core/frontend/src/api/sessions.ts", "r") as f:
    content = f.read()

content = content.replace(
    '''  restore: (sessionId: string, wsId: string, checkpointId: string) =>
    api.post<{ execution_id: string }>(
      `/sessions/${sessionId}/worker-sessions/${wsId}/checkpoints/${checkpointId}/restore`,
    ),''',
    '''  restore: (sessionId: string, wsId: string, checkpointId: string) =>
    api.post<{ execution_id: string }>(
      `/sessions/${sessionId}/worker-sessions/${wsId}/checkpoints/${checkpointId}/restore`,
    ),

  updateStar: (sessionId: string, wsId: string, checkpointId: string, isStarred: boolean) =>
    api.put<{ success: boolean }>(
      `/sessions/${sessionId}/worker-sessions/${wsId}/checkpoints/${checkpointId}/star`,
      { is_starred: isStarred }
    ),'''
)

with open("core/frontend/src/api/sessions.ts", "w") as f:
    f.write(content)
