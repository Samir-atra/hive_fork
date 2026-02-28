import { api } from "./client";
import type { DebugSession, DebugCheckpoint, Checkpoint } from "./types";

export const debugApi = {
  async getSession(sessionId: string): Promise<DebugSession> {
    return api.get<DebugSession>(`/sessions/${sessionId}/debug`);
  },

  async getCheckpoints(sessionId: string): Promise<Checkpoint[]> {
    return api.get<Checkpoint[]>(`/sessions/${sessionId}/checkpoints`);
  },

  async getCheckpoint(
    sessionId: string,
    checkpointId: string
  ): Promise<DebugCheckpoint> {
    return api.get<DebugCheckpoint>(
      `/sessions/${sessionId}/checkpoints/${checkpointId}`
    );
  },

  async getMemory(sessionId: string): Promise<Record<string, unknown>> {
    return api.get<Record<string, unknown>>(
      `/sessions/${sessionId}/debug/memory`
    );
  },

  async getNodeConversation(
    sessionId: string,
    nodeId: string
  ): Promise<string[]> {
    return api.get<string[]>(
      `/sessions/${sessionId}/debug/nodes/${nodeId}/conversation`
    );
  },

  async stepForward(sessionId: string): Promise<{ node_id: string | null }> {
    return api.post<{ node_id: string | null }>(
      `/sessions/${sessionId}/debug/step-forward`
    );
  },

  async stepBackward(sessionId: string): Promise<{ node_id: string | null }> {
    return api.post<{ node_id: string | null }>(
      `/sessions/${sessionId}/debug/step-backward`
    );
  },

  async resume(sessionId: string): Promise<void> {
    return api.post<void>(`/sessions/${sessionId}/debug/resume`);
  },

  async inspect(
    sessionId: string,
    expression: string
  ): Promise<{ result: unknown }> {
    return api.post<{ result: unknown }>(
      `/sessions/${sessionId}/debug/inspect`,
      { expression }
    );
  },
};
