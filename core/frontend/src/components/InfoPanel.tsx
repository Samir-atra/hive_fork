import { useState, useEffect, useCallback } from "react";
import {
  Info,
  RefreshCw,
  Loader2,
  FileText,
  Settings,
  Target,
  Tag,
  Clock,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { agentsApi } from "@/api/agents";
import type { NodeSpec, DiscoverEntry } from "@/api/types";

interface InfoPanelProps {
  sessionId: string | null;
  agentPath: string | null;
  nodeSpecs: NodeSpec[];
  disabled?: boolean;
}

function InfoRow({
  icon: Icon,
  label,
  value,
  className,
}: {
  icon: typeof Info;
  label: string;
  value: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex items-start gap-3 py-2", className)}>
      <Icon className="h-4 w-4 text-muted-foreground mt-0.5 flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-xs text-muted-foreground">{label}</p>
        <div className="text-sm font-medium mt-0.5">{value}</div>
      </div>
    </div>
  );
}

export default function InfoPanel({
  sessionId,
  agentPath,
  nodeSpecs,
  disabled = false,
}: InfoPanelProps) {
  const [agentInfo, setAgentInfo] = useState<DiscoverEntry | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchInfo = useCallback(async () => {
    if (!agentPath) return;
    setLoading(true);
    setError(null);
    try {
      const discovered = await agentsApi.discover();
      const allAgents = Object.values(discovered).flat();
      const info = allAgents.find((a) => a.path === agentPath);
      setAgentInfo(info || null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load agent info");
    } finally {
      setLoading(false);
    }
  }, [agentPath]);

  useEffect(() => {
    fetchInfo();
  }, [fetchInfo]);

  if (!sessionId && !agentPath) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        <p className="text-sm">Load an agent to view info</p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-border/40 px-4 py-3">
        <div className="flex items-center gap-2">
          <Info className="h-4 w-4 text-cyan-500" />
          <h3 className="text-sm font-semibold">Agent Info</h3>
        </div>
        <button
          onClick={fetchInfo}
          disabled={loading || disabled}
          className="rounded-md p-1.5 text-muted-foreground hover:bg-muted/60 hover:text-foreground disabled:opacity-50"
          title="Refresh"
        >
          <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
        </button>
      </div>

      {error && (
        <div className="mx-4 mt-3 rounded-md bg-red-500/10 px-3 py-2 text-xs text-red-400">
          {error}
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {loading ? (
          <div className="flex h-32 items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <>
            {agentInfo && (
              <div className="space-y-1">
                <h4 className="text-base font-semibold">{agentInfo.name}</h4>
                <p className="text-sm text-muted-foreground">
                  {agentInfo.description}
                </p>
              </div>
            )}

            <div className="rounded-lg border border-border/40 divide-y divide-border/40">
              {agentInfo && (
                <>
                  <div className="px-4">
                    <InfoRow
                      icon={FileText}
                      label="Path"
                      value={
                        <span className="font-mono text-xs break-all">
                          {agentInfo.path}
                        </span>
                      }
                    />
                  </div>
                  <div className="px-4">
                    <InfoRow
                      icon={Tag}
                      label="Category"
                      value={agentInfo.category}
                    />
                  </div>
                  <div className="px-4">
                    <InfoRow
                      icon={Settings}
                      label="Nodes / Tools"
                      value={`${agentInfo.node_count} / ${agentInfo.tool_count}`}
                    />
                  </div>
                  {agentInfo.last_active && (
                    <div className="px-4">
                      <InfoRow
                        icon={Clock}
                        label="Last Active"
                        value={new Date(agentInfo.last_active).toLocaleString()}
                      />
                    </div>
                  )}
                </>
              )}
              {nodeSpecs.length > 0 && (
                <div className="px-4">
                  <InfoRow
                    icon={Target}
                    label="Active Sessions"
                    value={agentInfo?.session_count ?? 0}
                  />
                </div>
              )}
            </div>

            {agentInfo && agentInfo.tags.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                  Tags
                </h4>
                <div className="flex flex-wrap gap-1.5">
                  {agentInfo.tags.map((tag) => (
                    <span
                      key={tag}
                      className="inline-flex items-center rounded-full bg-muted/60 px-2.5 py-0.5 text-xs font-medium"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {nodeSpecs.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                  Node Overview
                </h4>
                <div className="space-y-2">
                  {nodeSpecs.map((node) => (
                    <div
                      key={node.id}
                      className="rounded-lg border border-border/40 p-3"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">{node.name}</span>
                        <span className="text-xs text-muted-foreground">
                          {node.node_type}
                        </span>
                      </div>
                      {node.description && (
                        <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                          {node.description}
                        </p>
                      )}
                      {node.tools.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1">
                          {node.tools.slice(0, 5).map((tool) => (
                            <span
                              key={tool}
                              className="inline-flex items-center rounded bg-muted/40 px-1.5 py-0.5 text-xs"
                            >
                              {tool}
                            </span>
                          ))}
                          {node.tools.length > 5 && (
                            <span className="text-xs text-muted-foreground">
                              +{node.tools.length - 5} more
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
