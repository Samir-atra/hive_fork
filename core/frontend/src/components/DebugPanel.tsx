import { useState, useEffect, useCallback } from "react";
import {
  Bug,
  Play,
  SkipForward,
  SkipBack,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  Loader2,
  Terminal,
  Database,
  Activity,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { debugApi } from "@/api/debug";
import type { Checkpoint, NodeSpec } from "@/api/types";

interface DebugPanelProps {
  sessionId: string | null;
  nodeSpecs: NodeSpec[];
  disabled?: boolean;
}

function formatTimestamp(ts: string | null): string {
  if (!ts) return "N/A";
  try {
    const d = new Date(ts);
    return d.toLocaleTimeString();
  } catch {
    return ts;
  }
}

function CheckpointRow({
  checkpoint,
  isExpanded,
  onToggle,
  isActive,
}: {
  checkpoint: Checkpoint;
  isExpanded: boolean;
  onToggle: () => void;
  isActive: boolean;
}) {
  return (
    <div
      className={cn(
        "border-b border-border/40 last:border-b-0",
        isActive && "bg-primary/5"
      )}
    >
      <button
        onClick={onToggle}
        className={cn(
          "flex w-full items-center gap-3 px-3 py-2.5 text-left hover:bg-muted/40 transition-colors",
          isActive && "bg-primary/10"
        )}
      >
        {isExpanded ? (
          <ChevronDown className="h-4 w-4 text-muted-foreground flex-shrink-0" />
        ) : (
          <ChevronRight className="h-4 w-4 text-muted-foreground flex-shrink-0" />
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium truncate">
              {checkpoint.current_node || "Start"}
            </span>
            {isActive && (
              <span className="text-xs bg-primary/20 text-primary px-1.5 py-0.5 rounded">
                Current
              </span>
            )}
          </div>
          <span className="text-xs text-muted-foreground">
            {formatTimestamp(checkpoint.timestamp)}
          </span>
        </div>
        {!checkpoint.is_clean && (
          <span className="text-xs text-orange-500">dirty</span>
        )}
      </button>
      {isExpanded && (
        <div className="bg-muted/20 px-3 pb-3 pt-1 space-y-2">
          <div className="text-xs">
            <span className="text-muted-foreground">ID: </span>
            <span className="font-mono">{checkpoint.checkpoint_id.slice(0, 12)}...</span>
          </div>
          {checkpoint.next_node && (
            <div className="text-xs">
              <span className="text-muted-foreground">Next: </span>
              <span>{checkpoint.next_node}</span>
            </div>
          )}
          {checkpoint.error && (
            <div className="rounded-md bg-red-500/10 p-2">
              <p className="text-xs font-mono text-red-400 whitespace-pre-wrap">
                {checkpoint.error}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function DebugPanel({
  sessionId,
  nodeSpecs,
  disabled = false,
}: DebugPanelProps) {
  const [checkpoints, setCheckpoints] = useState<Checkpoint[]>([]);
  const [memory, setMemory] = useState<Record<string, unknown>>({});
  const [loading, setLoading] = useState(false);
  const [stepping, setStepping] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedCheckpoints, setExpandedCheckpoints] = useState<Set<string>>(new Set());
  const [activeTab, setActiveTab] = useState<"checkpoints" | "memory">("checkpoints");
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [nodeConversation, setNodeConversation] = useState<string[]>([]);

  const fetchData = useCallback(async () => {
    if (!sessionId) return;
    setLoading(true);
    setError(null);
    try {
      const [checkpointsData, memoryData] = await Promise.all([
        debugApi.getCheckpoints(sessionId).catch(() => []),
        debugApi.getMemory(sessionId).catch(() => ({})),
      ]);
      setCheckpoints(checkpointsData);
      setMemory(memoryData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load debug data");
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleStepForward = async () => {
    if (!sessionId) return;
    setStepping(true);
    try {
      await debugApi.stepForward(sessionId);
      await fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Step forward failed");
    } finally {
      setStepping(false);
    }
  };

  const handleStepBackward = async () => {
    if (!sessionId) return;
    setStepping(true);
    try {
      await debugApi.stepBackward(sessionId);
      await fetchData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Step backward failed");
    } finally {
      setStepping(false);
    }
  };

  const handleResume = async () => {
    if (!sessionId) return;
    try {
      await debugApi.resume(sessionId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Resume failed");
    }
  };

  const handleNodeSelect = async (nodeId: string) => {
    if (!sessionId) return;
    setSelectedNode(nodeId);
    try {
      const conversation = await debugApi.getNodeConversation(sessionId, nodeId);
      setNodeConversation(conversation);
    } catch {
      setNodeConversation([]);
    }
  };

  const toggleExpanded = (checkpointId: string) => {
    setExpandedCheckpoints((prev) => {
      const next = new Set(prev);
      if (next.has(checkpointId)) {
        next.delete(checkpointId);
      } else {
        next.add(checkpointId);
      }
      return next;
    });
  };

  const currentNodeId =
    checkpoints.length > 0
      ? checkpoints[checkpoints.length - 1].current_node
      : null;

  if (!sessionId) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        <p className="text-sm">Load an agent to debug</p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-border/40 px-4 py-3">
        <div className="flex items-center gap-2">
          <Bug className="h-4 w-4 text-orange-500" />
          <h3 className="text-sm font-semibold">Debugger</h3>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={fetchData}
            disabled={loading || disabled}
            className="rounded-md p-1.5 text-muted-foreground hover:bg-muted/60 hover:text-foreground disabled:opacity-50"
            title="Refresh"
          >
            <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
          </button>
        </div>
      </div>

      <div className="flex items-center justify-center gap-2 border-b border-border/40 px-4 py-2">
        <button
          onClick={handleStepBackward}
          disabled={stepping || disabled || checkpoints.length === 0}
          className="flex items-center gap-1 rounded-md bg-muted px-2 py-1 text-xs font-medium hover:bg-muted/80 disabled:opacity-50"
          title="Step Backward"
        >
          <SkipBack className="h-3.5 w-3.5" />
        </button>
        <button
          onClick={handleStepForward}
          disabled={stepping || disabled}
          className="flex items-center gap-1 rounded-md bg-orange-500 px-3 py-1 text-xs font-medium text-white hover:bg-orange-600 disabled:opacity-50"
          title="Step Forward"
        >
          {stepping ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <SkipForward className="h-3.5 w-3.5" />
          )}
          Step
        </button>
        <button
          onClick={handleResume}
          disabled={disabled}
          className="flex items-center gap-1 rounded-md bg-green-500 px-3 py-1 text-xs font-medium text-white hover:bg-green-600 disabled:opacity-50"
          title="Resume"
        >
          <Play className="h-3.5 w-3.5" />
          Resume
        </button>
      </div>

      {error && (
        <div className="mx-4 mt-3 rounded-md bg-red-500/10 px-3 py-2 text-xs text-red-400">
          {error}
        </div>
      )}

      <div className="flex border-b border-border/40">
        <button
          onClick={() => setActiveTab("checkpoints")}
          className={cn(
            "flex-1 px-4 py-2 text-xs font-medium transition-colors",
            activeTab === "checkpoints"
              ? "border-b-2 border-primary text-foreground"
              : "text-muted-foreground hover:text-foreground"
          )}
        >
          <Activity className="h-3.5 w-3.5 inline mr-1.5" />
          Checkpoints
        </button>
        <button
          onClick={() => setActiveTab("memory")}
          className={cn(
            "flex-1 px-4 py-2 text-xs font-medium transition-colors",
            activeTab === "memory"
              ? "border-b-2 border-primary text-foreground"
              : "text-muted-foreground hover:text-foreground"
          )}
        >
          <Database className="h-3.5 w-3.5 inline mr-1.5" />
          Memory
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex h-32 items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : activeTab === "checkpoints" ? (
          checkpoints.length === 0 ? (
            <div className="flex h-32 items-center justify-center text-muted-foreground">
              <p className="text-sm">No checkpoints available</p>
            </div>
          ) : (
            <div>
              {checkpoints.map((cp) => (
                <CheckpointRow
                  key={cp.checkpoint_id}
                  checkpoint={cp}
                  isExpanded={expandedCheckpoints.has(cp.checkpoint_id)}
                  onToggle={() => toggleExpanded(cp.checkpoint_id)}
                  isActive={cp.current_node === currentNodeId}
                />
              ))}
            </div>
          )
        ) : (
          <div className="p-3">
            <div className="rounded-md bg-muted/40 p-3">
              <pre className="text-xs font-mono text-muted-foreground whitespace-pre-wrap overflow-x-auto">
                {JSON.stringify(memory, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>

      {nodeSpecs.length > 0 && (
        <div className="border-t border-border/40">
          <div className="px-4 py-2">
            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Node Inspector
            </h4>
          </div>
          <div className="max-h-40 overflow-y-auto">
            <select
              value={selectedNode || ""}
              onChange={(e) => handleNodeSelect(e.target.value)}
              className="w-full bg-background px-3 py-2 text-sm border-0 focus:ring-0"
            >
              <option value="">Select a node...</option>
              {nodeSpecs.map((node) => (
                <option key={node.id} value={node.id}>
                  {node.name} ({node.node_type})
                </option>
              ))}
            </select>
            {nodeConversation.length > 0 && (
              <div className="p-3 border-t border-border/40">
                <div className="flex items-center gap-2 mb-2">
                  <Terminal className="h-3.5 w-3.5 text-muted-foreground" />
                  <span className="text-xs font-medium">Conversation</span>
                </div>
                <div className="rounded-md bg-muted/40 p-2 max-h-24 overflow-y-auto">
                  {nodeConversation.map((line, idx) => (
                    <p key={idx} className="text-xs font-mono text-muted-foreground whitespace-pre-wrap">
                      {line}
                    </p>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
