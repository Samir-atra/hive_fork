with open("core/frontend/src/components/AgentGraph.tsx", "r") as f:
    content = f.read()

content = content.replace(
    'import { Play, Pause, Loader2, CheckCircle2 } from "lucide-react";',
    'import { Play, Pause, Loader2, CheckCircle2, Bookmark, BookmarkPlus, RotateCcw } from "lucide-react";\nimport * as DropdownMenu from "@radix-ui/react-dropdown-menu";\nimport { type Checkpoint } from "@/api/types";'
)

content = content.replace(
    '  queenPhase?: string;',
    '  queenPhase?: string;\n  checkpoints?: Checkpoint[];\n  onStarCheckpoint?: (cpId: string, isStarred: boolean) => void;\n  onRestoreCheckpoint?: (cpId: string) => void;'
)

content = content.replace(
    'export default function AgentGraph({ nodes, title: _title, onNodeClick, onRun, onPause, version, runState: externalRunState, building, queenPhase }: AgentGraphProps) {',
    'export default function AgentGraph({ nodes, title: _title, onNodeClick, onRun, onPause, version, runState: externalRunState, building, queenPhase, checkpoints = [], onStarCheckpoint, onRestoreCheckpoint }: AgentGraphProps) {'
)

checkpoint_menu = '''
          <div className="flex items-center gap-2">
            <p className="text-[11px] text-muted-foreground font-medium uppercase tracking-wider">Pipeline</p>
            {version && (
              <span className="text-[10px] font-mono font-medium text-muted-foreground/60 border border-border/30 rounded px-1 py-0.5 leading-none">
                {version}
              </span>
            )}

            {checkpoints && checkpoints.length > 0 && (
              <DropdownMenu.Root>
                <DropdownMenu.Trigger asChild>
                  <button className="flex items-center justify-center w-5 h-5 rounded hover:bg-muted text-muted-foreground transition-colors" title="Checkpoints">
                    <Bookmark className="w-3.5 h-3.5" />
                  </button>
                </DropdownMenu.Trigger>
                <DropdownMenu.Portal>
                  <DropdownMenu.Content className="z-50 min-w-[200px] bg-popover border border-border rounded-md shadow-md py-1 mr-2 animate-in fade-in-80 zoom-in-95 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95">
                    <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground flex items-center gap-1.5 border-b border-border/50 mb-1">
                      <Bookmark className="w-3 h-3" />
                      Checkpoints
                    </div>
                    <div className="max-h-[300px] overflow-y-auto">
                      {checkpoints.map(cp => (
                        <div key={cp.checkpoint_id} className="group flex items-center justify-between px-2 py-1.5 hover:bg-muted/50 cursor-default">
                          <div className="flex flex-col min-w-0 pr-3">
                            <span className="text-xs text-foreground truncate">{cp.checkpoint_id}</span>
                            <span className="text-[10px] text-muted-foreground">Node: {cp.current_node || "unknown"}</span>
                          </div>
                          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                            <button
                              onClick={() => onRestoreCheckpoint?.(cp.checkpoint_id)}
                              className="p-1 rounded text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                              title="Restore checkpoint"
                            >
                              <RotateCcw className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => onStarCheckpoint?.(cp.checkpoint_id, !cp.is_starred)}
                              className={`p-1 rounded transition-colors ${cp.is_starred ? "text-amber-500 hover:bg-amber-500/10" : "text-muted-foreground hover:bg-muted hover:text-foreground"}`}
                              title={cp.is_starred ? "Unstar checkpoint" : "Star checkpoint"}
                            >
                              {cp.is_starred ? <Bookmark className="w-3.5 h-3.5 fill-current" /> : <BookmarkPlus className="w-3.5 h-3.5" />}
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </DropdownMenu.Content>
                </DropdownMenu.Portal>
              </DropdownMenu.Root>
            )}
          </div>
'''

content = content.replace(
    '''          <div className="flex items-center gap-2">
            <p className="text-[11px] text-muted-foreground font-medium uppercase tracking-wider">Pipeline</p>
            {version && (
              <span className="text-[10px] font-mono font-medium text-muted-foreground/60 border border-border/30 rounded px-1 py-0.5 leading-none">
                {version}
              </span>
            )}
          </div>''',
    checkpoint_menu
)

content = content.replace(
    '''        <div className="flex items-center gap-2">
          <p className="text-[11px] text-muted-foreground font-medium uppercase tracking-wider">Pipeline</p>
          {version && (
            <span className="text-[10px] font-mono font-medium text-muted-foreground/60 border border-border/30 rounded px-1 py-0.5 leading-none">
              {version}
            </span>
          )}
        </div>''',
    checkpoint_menu
)

with open("core/frontend/src/components/AgentGraph.tsx", "w") as f:
    f.write(content)
