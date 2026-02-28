import { useState, useEffect, useCallback } from "react";
import {
  TestTube,
  Play,
  CheckCircle,
  XCircle,
  Clock,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { testApi } from "@/api/test";
import type { TestCase, TestResult, TestRunSummary } from "@/api/types";

interface TestPanelProps {
  sessionId: string | null;
  disabled?: boolean;
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

function TestResultRow({
  result,
  isExpanded,
  onToggle,
}: {
  result: TestResult;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="border-b border-border/40 last:border-b-0">
      <button
        onClick={onToggle}
        className="flex w-full items-center gap-3 px-3 py-2.5 text-left hover:bg-muted/40 transition-colors"
      >
        {isExpanded ? (
          <ChevronDown className="h-4 w-4 text-muted-foreground flex-shrink-0" />
        ) : (
          <ChevronRight className="h-4 w-4 text-muted-foreground flex-shrink-0" />
        )}
        {result.passed ? (
          <CheckCircle className="h-4 w-4 text-green-500 flex-shrink-0" />
        ) : (
          <XCircle className="h-4 w-4 text-red-500 flex-shrink-0" />
        )}
        <span className="flex-1 truncate text-sm font-medium">
          {result.test_name}
        </span>
        <span className="text-xs text-muted-foreground">
          {formatDuration(result.duration_ms)}
        </span>
      </button>
      {isExpanded && (
        <div className="bg-muted/20 px-3 pb-3 pt-1">
          {result.error && (
            <div className="mb-2 rounded-md bg-red-500/10 p-2">
              <p className="text-xs font-mono text-red-400 whitespace-pre-wrap">
                {result.error}
              </p>
            </div>
          )}
          {result.output && (
            <div className="rounded-md bg-muted/40 p-2">
              <p className="text-xs font-mono text-muted-foreground whitespace-pre-wrap">
                {JSON.stringify(result.output, null, 2)}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function TestPanel({ sessionId, disabled = false }: TestPanelProps) {
  const [tests, setTests] = useState<TestCase[]>([]);
  const [results, setResults] = useState<TestRunSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedTests, setExpandedTests] = useState<Set<string>>(new Set());

  const fetchTests = useCallback(async () => {
    if (!sessionId) return;
    setLoading(true);
    setError(null);
    try {
      const [testList, testResults] = await Promise.all([
        testApi.list(sessionId),
        testApi.getResults(sessionId).catch(() => null),
      ]);
      setTests(testList);
      setResults(testResults);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load tests");
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    fetchTests();
  }, [fetchTests]);

  const handleRunAll = async () => {
    if (!sessionId) return;
    setRunning(true);
    setError(null);
    try {
      const summary = await testApi.runAll(sessionId);
      setResults(summary);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run tests");
    } finally {
      setRunning(false);
    }
  };

  const handleRunTest = async (testName: string) => {
    if (!sessionId) return;
    setRunning(true);
    setError(null);
    try {
      const summary = await testApi.run(sessionId, testName);
      setResults((prev) => {
        if (!prev) return summary;
        const existingIdx = prev.results.findIndex(
          (r) => r.test_name === testName
        );
        const newResults = [...prev.results];
        if (existingIdx >= 0) {
          newResults[existingIdx] = summary.results[0];
        } else {
          newResults.push(summary.results[0]);
        }
        return {
          ...prev,
          results: newResults,
          passed: newResults.filter((r) => r.passed).length,
          failed: newResults.filter((r) => !r.passed).length,
        };
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run test");
    } finally {
      setRunning(false);
    }
  };

  const toggleExpanded = (testName: string) => {
    setExpandedTests((prev) => {
      const next = new Set(prev);
      if (next.has(testName)) {
        next.delete(testName);
      } else {
        next.add(testName);
      }
      return next;
    });
  };

  if (!sessionId) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        <p className="text-sm">Load an agent to run tests</p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-border/40 px-4 py-3">
        <div className="flex items-center gap-2">
          <TestTube className="h-4 w-4 text-blue-500" />
          <h3 className="text-sm font-semibold">Tests</h3>
          {results && (
            <span className="ml-2 flex items-center gap-1 text-xs text-muted-foreground">
              <span className="text-green-500">{results.passed}</span>/
              <span className="text-red-500">{results.failed}</span> passed
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchTests}
            disabled={loading || disabled}
            className="rounded-md p-1.5 text-muted-foreground hover:bg-muted/60 hover:text-foreground disabled:opacity-50"
            title="Refresh"
          >
            <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
          </button>
          <button
            onClick={handleRunAll}
            disabled={running || disabled || tests.length === 0}
            className="flex items-center gap-1.5 rounded-md bg-blue-500 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {running ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Play className="h-3.5 w-3.5" />
            )}
            Run All
          </button>
        </div>
      </div>

      {error && (
        <div className="mx-4 mt-3 rounded-md bg-red-500/10 px-3 py-2 text-xs text-red-400">
          {error}
        </div>
      )}

      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex h-32 items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : tests.length === 0 ? (
          <div className="flex h-32 items-center justify-center text-muted-foreground">
            <p className="text-sm">No tests found</p>
          </div>
        ) : (
          <div className="divide-y divide-border/40">
            {tests.map((test) => {
              const result = results?.results.find(
                (r) => r.test_name === test.name
              );
              return (
                <div key={test.name} className="p-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {result?.passed ? (
                        <CheckCircle className="h-4 w-4 text-green-500" />
                      ) : result ? (
                        <XCircle className="h-4 w-4 text-red-500" />
                      ) : (
                        <Clock className="h-4 w-4 text-muted-foreground" />
                      )}
                      <span className="text-sm font-medium">{test.name}</span>
                    </div>
                    <button
                      onClick={() => handleRunTest(test.name)}
                      disabled={running || disabled}
                      className="rounded-md p-1 text-muted-foreground hover:bg-muted/60 hover:text-foreground disabled:opacity-50"
                      title="Run test"
                    >
                      <Play className="h-3.5 w-3.5" />
                    </button>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground line-clamp-2">
                    {test.description}
                  </p>
                </div>
              );
            })}
          </div>
        )}

        {results && results.results.length > 0 && (
          <div className="border-t border-border/40">
            <div className="px-4 py-2">
              <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Results
              </h4>
            </div>
            <div>
              {results.results.map((result) => (
                <TestResultRow
                  key={result.test_name}
                  result={result}
                  isExpanded={expandedTests.has(result.test_name)}
                  onToggle={() => toggleExpanded(result.test_name)}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
