with open("core/frontend/src/pages/workspace.tsx", "r") as f:
    content = f.read()

content = content.replace(
    'import type { LiveSession, AgentEvent, DiscoverEntry, NodeSpec, DraftGraph as DraftGraphData } from "@/api/types";',
    'import type { LiveSession, AgentEvent, DiscoverEntry, NodeSpec, DraftGraph as DraftGraphData, Checkpoint } from "@/api/types";'
)

# Insert Checkpoints state
state_insertion = '''  const [newTabOpen, setNewTabOpen] = useState(false);
  const newTabBtnRef = useRef<HTMLButtonElement>(null);

  // -- Checkpoints State --
  const [checkpoints, setCheckpoints] = useState<Checkpoint[]>([]);
'''
content = content.replace(
    '  const [newTabOpen, setNewTabOpen] = useState(false);\n  const newTabBtnRef = useRef<HTMLButtonElement>(null);',
    state_insertion
)

fetch_checkpoints = '''
  // -- Fetch Checkpoints --
  useEffect(() => {
    const state = agentStates[activeWorker];
    if (state && state.sessionId && !state.workerRunState.includes("running")) {
      sessionsApi.checkpoints(state.sessionId, state.agentPath || activeWorker)
        .then(res => setCheckpoints(res.checkpoints || []))
        .catch(() => setCheckpoints([]));
    } else if (!state?.sessionId) {
      setCheckpoints([]);
    }
  }, [activeWorker, agentStates, activeAgentState?.workerRunState]);

  const handleStarCheckpoint = async (cpId: string, isStarred: boolean) => {
    const state = agentStates[activeWorker];
    if (!state || !state.sessionId) return;
    try {
      await sessionsApi.updateStar(state.sessionId, state.agentPath || activeWorker, cpId, isStarred);
      setCheckpoints(prev => prev.map(c => c.checkpoint_id === cpId ? { ...c, is_starred: isStarred } : c));
    } catch (e) {
      console.error("Failed to star checkpoint", e);
    }
  };

  const handleRestoreCheckpoint = async (cpId: string) => {
    const state = agentStates[activeWorker];
    if (!state || !state.sessionId) return;
    try {
      await sessionsApi.restore(state.sessionId, state.agentPath || activeWorker, cpId);
      // Let SSE events handle the actual state updates after restore triggers an execution
    } catch (e) {
      console.error("Failed to restore checkpoint", e);
    }
  };
'''

content = content.replace(
    '  // --- NewTabPopover ---',
    fetch_checkpoints + '\n  // --- NewTabPopover ---'
)

content = content.replace(
    '''              <AgentGraph
                nodes={currentGraph.nodes}
                title={currentGraph.title}
                onNodeClick={(node) => setSelectedNode(prev => prev?.id === node.id ? null : node)}
                onRun={handleRun}
                onPause={handlePause}
                runState={activeAgentState?.workerRunState ?? "idle"}
                building={activeAgentState?.queenBuilding ?? false}
                queenPhase={activeAgentState?.queenPhase ?? "building"}
              />''',
    '''              <AgentGraph
                nodes={currentGraph.nodes}
                title={currentGraph.title}
                onNodeClick={(node) => setSelectedNode(prev => prev?.id === node.id ? null : node)}
                onRun={handleRun}
                onPause={handlePause}
                runState={activeAgentState?.workerRunState ?? "idle"}
                building={activeAgentState?.queenBuilding ?? false}
                queenPhase={activeAgentState?.queenPhase ?? "building"}
                checkpoints={checkpoints}
                onStarCheckpoint={handleStarCheckpoint}
                onRestoreCheckpoint={handleRestoreCheckpoint}
              />'''
)

with open("core/frontend/src/pages/workspace.tsx", "w") as f:
    f.write(content)
