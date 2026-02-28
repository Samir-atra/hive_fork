import { api } from "./client";
import type { TestRunSummary, TestCase, TestResult } from "./types";

export const testApi = {
  async list(sessionId: string): Promise<TestCase[]> {
    return api.get<TestCase[]>(`/sessions/${sessionId}/tests`);
  },

  async run(
    sessionId: string,
    testName?: string,
    category?: string
  ): Promise<TestRunSummary> {
    const params = new URLSearchParams();
    if (testName) params.set("test", testName);
    if (category) params.set("category", category);
    const query = params.toString() ? `?${params.toString()}` : "";
    return api.post<TestRunSummary>(
      `/sessions/${sessionId}/tests/run${query}`
    );
  },

  async runAll(sessionId: string): Promise<TestRunSummary> {
    return api.post<TestRunSummary>(`/sessions/${sessionId}/tests/run-all`);
  },

  async getResults(sessionId: string): Promise<TestRunSummary> {
    return api.get<TestRunSummary>(`/sessions/${sessionId}/tests/results`);
  },

  async getResult(
    sessionId: string,
    testName: string
  ): Promise<TestResult> {
    return api.get<TestResult>(
      `/sessions/${sessionId}/tests/results/${encodeURIComponent(testName)}`
    );
  },

  async create(
    sessionId: string,
    testCase: TestCase
  ): Promise<{ name: string }> {
    return api.post<{ name: string }>(
      `/sessions/${sessionId}/tests`,
      testCase
    );
  },

  async delete(sessionId: string, testName: string): Promise<void> {
    return api.delete<void>(
      `/sessions/${sessionId}/tests/${encodeURIComponent(testName)}`
    );
  },
};
