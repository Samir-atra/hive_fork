import React, { useState, useEffect } from 'react';
import { 
  Book, 
  Target, 
  Activity, 
  Theater, 
  Monitor, 
  ShieldCheck, 
  Zap, 
  Settings,
  ChevronRight,
  Loader2,
  CheckCircle,
  Cpu,
  Info,
  BookOpen
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import './styles/App.css';
import DataModule from './components/DataModule';
import ArtifactView from './components/ArtifactView';
import MarkdownView from './components/MarkdownView';

interface NavItemProps {
  id: string;
  icon: React.ElementType;
  label: string;
  active: boolean;
  onClick: () => void;
}

/**
 * Component for rendering individual navigation items in the sidebar.
 * 
 * @param {NavItemProps} props The properties for the navigation item.
 * @returns {React.ReactElement} The rendered navigation item.
 */
const NavItem: React.FC<NavItemProps> = ({ icon: Icon, label, active, onClick }) => (
  <div 
    className={`nav-item ${active ? 'active' : ''}`}
    onClick={onClick}
  >
    <Icon size={18} />
    <span>{label}</span>
  </div>
);

/**
 * Main application component for the Hive Agentic Platform.
 * 
 * Manages module state, agent generation workflow, and data fetching from the backend.
 * 
 * @returns {React.ReactElement} The main application layout.
 */
const App: React.FC = () => {
  const [activeModule, setActiveModule] = useState('studio');
  const [prompt, setPrompt] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [steps, setSteps] = useState<{ icon: any, text: string, time?: string, report?: string }[]>([]);
  const [showReport, setShowReport] = useState(false);
  const [finalReport, setFinalReport] = useState('');
  const [docsContent, setDocsContent] = useState('');
  const [evolutionData, setEvolutionData] = useState<any[]>([]);
  const [cinemaData, setCinemaData] = useState<any>(null);

  const modules = [
    { id: 'docs', icon: Book, label: 'Documentation' },
    { id: 'studio', icon: Target, label: 'Goal Studio' },
    { id: 'generation', icon: Activity, label: 'Live Generation' },
    { id: 'theater', icon: Theater, label: 'Evolution Theater' },
    { id: 'cinema', icon: Monitor, label: 'Execution Cinema' },
    { id: 'hitl', icon: ShieldCheck, label: 'HITL Center' },
  ];

  /**
   * Mapping of icon strings from the backend to Lucide-React components.
   * @type {Object.<string, React.ElementType>}
   */
  const iconMap: Record<string, React.ElementType> = { 
    Cpu, 
    Target, 
    Zap, 
    CheckCircle, 
    Loader2, 
    CpuIcon: Cpu,
    Info,
    Monitor,
    ShieldCheck,
    Theater,
    Book
  };

  useEffect(() => {
    const fetchAux = async () => {
      if (activeModule === 'docs') {
         const res = await fetch('http://localhost:8000/docs_content').catch(() => null);
         if (res) { const data = await res.json(); setDocsContent(data.content); }
      }
      if (activeModule === 'theater') {
         const res = await fetch('http://localhost:8000/evolution').catch(() => null);
         if (res) { const data = await res.json(); setEvolutionData(data); }
      }
      if (activeModule === 'cinema') {
         const res = await fetch('http://localhost:8000/cinema').catch(() => null);
         if (res) { const data = await res.json(); setCinemaData(data); }
      }
    };
    fetchAux();

    let interval: any;
    if (activeModule === 'generation' && !showReport) {
      interval = setInterval(async () => {
        try {
          const res = await fetch('http://localhost:8000/activity');
          const data = await res.json();
          if (data && data.length > 0) {
            const formatted = data.map((s: any) => ({
              icon: iconMap[s.icon] || Info,
              text: s.text,
              report: s.report
            }));
            setSteps(formatted);
            const last = data[data.length - 1];
            if (last.report) {
              setFinalReport(last.report);
              setShowReport(true);
              clearInterval(interval);
            }
          }
        } catch (e) {
          // Fallback if backend is down - quiet
        }
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [activeModule, showReport]);

  const handleGenerate = async () => {
    if (!prompt) return;
    
    // Try real backend call
    try {
      setIsGenerating(true);
      const res = await fetch('http://localhost:8000/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt })
      });
      
      if (res.ok) {
        setSteps([{ icon: Cpu, text: 'Connecting to Hive Engine...' }]);
        setShowReport(false);
        setFinalReport('');
        setEvolutionData([]);
        setCinemaData(null);
        setActiveModule('generation');
        setIsGenerating(false);
        return;
      }
    } catch (e) {
      console.log("Backend not detected, falling back to simulation.");
    }

    // FALLBACK: Simulation logic if backend fails
    setIsGenerating(true);
    setShowReport(false);
    setFinalReport('');
    setEvolutionData([]);
    setCinemaData(null);
    setSteps([
      { icon: Cpu, text: 'Initializing architecture engine...', time: '0ms' }
    ]);
    
    setTimeout(() => {
      setSteps(prev => [...prev, { icon: Target, text: `Goal set: ${prompt.slice(0, 30)}...`, time: '450ms' }]);
    }, 800);

    setTimeout(() => {
      setSteps(prev => [...prev, { icon: Zap, text: 'Architecting Agent Graph (Gemini 2.5 Flash)...', time: '1.2s' }]);
    }, 1500);

    setTimeout(() => {
      setSteps(prev => [...prev, { icon: CheckCircle, text: 'Agent Blueprint Generated: [github-discovery]', time: '2.1s' }]);
      setIsGenerating(false);
      setActiveModule('generation');
      
      setTimeout(() => {
        setSteps(prev => [...prev, { icon: Loader2, text: 'Executing: Node [analyzer] -> Parsing intent...', time: '3.5s' }]);
      }, 1000);
      
      setTimeout(() => {
        setSteps(prev => [...prev, { icon: Loader2, text: 'Executing: Node [searcher] -> Calling GitHub API...', time: '5.0s' }]);
      }, 2500);

      setTimeout(() => {
        setSteps(prev => [...prev, { icon: Loader2, text: 'Executing: Node [reporter] -> Summarizing issues...', time: '7.0s' }]);
      }, 4500);

      setTimeout(() => {
        setSteps(prev => [...prev, { icon: CheckCircle, text: 'Workflow Complete. Report available in Cinema.', time: '8.5s' }]);
        setFinalReport(`Simulation Report for ${prompt}: Found 5 matching items.`);
        setShowReport(true);
      }, 6000);

    }, 3000);
  };

  return (
    <div className="app-container">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="logo-section">
          <div className="logo-icon">
            <Zap size={24} fill="white" color="white" />
          </div>
          <div className="logo-text">
            <h1>HIVE</h1>
            <p>Agentic Platform</p>
          </div>
        </div>

        <nav className="nav-list">
          {modules.map((m) => (
            <NavItem 
              key={m.id}
              {...m}
              active={activeModule === m.id}
              onClick={() => setActiveModule(m.id)}
            />
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="status-card">
            <div className="flex items-center gap-2" style={{ marginBottom: '0.5rem' }}>
              <div style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: 'var(--success)', boxShadow: '0 0 10px var(--success)' }} />
              <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>System Active</span>
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'monospace' }}>
              v0.1.0-alpha
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="main-area">
        <header className="main-header">
          <div className="flex items-center gap-2">
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Workspace</span>
            <ChevronRight size={12} color="var(--text-muted)" />
            <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>{activeModule.toUpperCase()}</span>
          </div>
          <div className="flex items-center gap-3">
            <button className="icon-btn" style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}>
              <Settings size={20} />
            </button>
            <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'linear-gradient(45deg, #2a2a32, #16161c)', border: '1px solid var(--glass-border)' }} />
          </div>
        </header>

        <div className="content-body">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeModule}
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 1.02 }}
              transition={{ duration: 0.2 }}
              style={{ height: '100%' }}
            >
              {activeModule === 'studio' && (
                <div className="studio-view">
                  <div className="studio-hero">
                    <h2 className="gradient-text">Define your goal.</h2>
                    <p>Describe what you want the agent to achieve. Hive will generate the optimal execution graph.</p>
                  </div>

                  <div className="input-container">
                    <textarea 
                      className="prompt-area"
                      value={prompt}
                      onChange={(e) => setPrompt(e.target.value)}
                      placeholder="e.g. Create a research agent that searches for the latest AI trends on Twitter and summarizes them into a PDF."
                    />
                    <button 
                      className="generate-btn"
                      onClick={handleGenerate}
                      disabled={!prompt || isGenerating}
                    >
                      {isGenerating ? <Loader2 size={18} className="spin" /> : <Zap size={18} fill="black" />}
                      <span>{isGenerating ? 'Architecting...' : 'Generate Agent'}</span>
                    </button>
                  </div>

                  <div style={{ marginBottom: '2.5rem' }}>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', display: 'block', marginBottom: '1rem' }}>Sample Prompts</span>
                    <div className="flex flex-wrap gap-3">
                      {[
                        "Find active issues in 'microsoft/vscode' labeled 'extension-host'.",
                        "Summarize the latest trends in Agentic AI from Twitter.",
                        "Analyze BTC and ETH performance and suggest a strategy."
                      ].map((p, idx) => (
                        <button 
                          key={idx}
                          onClick={() => setPrompt(p)}
                          style={{ 
                            padding: '0.6rem 1rem', 
                            background: 'rgba(255,255,255,0.03)', 
                            border: '1px solid var(--glass-border)', 
                            borderRadius: '20px', 
                            color: 'var(--text-secondary)', 
                            fontSize: '0.75rem', 
                            cursor: 'pointer',
                            transition: 'all 0.2s'
                          }}
                          onMouseOver={(e) => { e.currentTarget.style.borderColor = 'var(--primary)'; e.currentTarget.style.color = '#fff'; }}
                          onMouseOut={(e) => { e.currentTarget.style.borderColor = 'var(--glass-border)'; e.currentTarget.style.color = 'var(--text-secondary)'; }}
                        >
                          {p}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
                    <div style={{ padding: '1.5rem', borderRadius: 'var(--border-radius-lg)', backgroundColor: 'var(--bg-surface)', border: '1px solid var(--glass-border)' }}>
                      <h3 style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '1rem' }}>Capability Stack</h3>
                      <div className="flex flex-col gap-3">
                        <div className="flex items-center gap-2" style={{ fontSize: '0.875rem', color: '#cbd5e1' }}>
                          <CheckCircle size={16} color="var(--primary)" />
                          <span>Graph-based reasoning</span>
                        </div>
                        <div className="flex items-center gap-2" style={{ fontSize: '0.875rem', color: '#cbd5e1' }}>
                          <CheckCircle size={16} color="var(--primary)" />
                          <span>MCP Tool Integration</span>
                        </div>
                      </div>
                    </div>
                    <div style={{ padding: '1.5rem', borderRadius: 'var(--border-radius-lg)', border: '2px dashed var(--glass-border)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Drag constraints here</span>
                    </div>
                  </div>
                </div>
              )}

              {activeModule === 'docs' && (
                <div className="bg-surface rounded-2xl border border-glass overflow-hidden h-full flex flex-col">
                  <div className="px-8 py-5 border-b border-white/5 bg-white/2 backdrop-blur-md flex items-center justify-between">
                     <div className="flex items-center gap-3">
                        <BookOpen size={18} className="text-primary" />
                        <span className="text-xs font-black uppercase tracking-[0.2em]">Framework Documentation</span>
                     </div>
                     <div className="flex gap-2">
                        <div className="px-3 py-1 bg-white/5 rounded-full text-[10px] text-muted">v0.1.0-alpha</div>
                     </div>
                  </div>
                  <div className="flex-1 overflow-y-auto custom-scrollbar">
                     <MarkdownView content={docsContent} />
                  </div>
                </div>
              )}

              {activeModule === 'theater' && (
                 <div className="p-8 h-full flex flex-col gap-6 overflow-y-auto">
                    <h2 className="text-2xl font-bold gradient-text">Evolution Trace</h2>
                    <div className="grid gap-4">
                       {evolutionData.map((e, i) => (
                          <div key={i} className="p-4 bg-surface rounded-lg border border-glass flex justify-between items-center group hover:border-primary/50 transition-colors">
                             <div>
                                <span className="text-[10px] font-black text-primary block uppercase mb-1 tracking-widest bg-primary/10 w-fit px-2 py-0.5 rounded" style={{ background: 'linear-gradient(90deg, var(--primary), var(--secondary))', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>{e.stage}</span>
                                <span className="text-sm font-medium text-slate-200">{e.action}</span>
                             </div>
                             <span className="text-[10px] font-mono text-muted bg-white/5 px-2 py-1 rounded">{e.timestamp}</span>
                          </div>
                       ))}
                       {evolutionData.length === 0 && <p className="text-muted">No evolution trace present. Run an agent first.</p>}
                    </div>
                 </div>
              )}

              {activeModule === 'cinema' && (
                 <div className="p-8 h-full flex flex-col gap-6 overflow-y-auto">
                    <h2 className="text-2xl font-bold gradient-text">Execution Cinema</h2>
                    <div className="grid grid-cols-3 gap-6 mb-8">
                       <div className="p-5 bg-surface rounded-xl border border-glass relative overflow-hidden group">
                          <div className="absolute top-0 left-0 w-1 h-full bg-primary" />
                          <span className="text-[10px] text-muted font-bold uppercase block mb-1 tracking-widest">Total Nodes</span>
                          <span className="text-3xl font-black gradient-text">{cinemaData?.metrics?.total_nodes ?? 0}</span>
                       </div>
                       <div className="p-5 bg-surface rounded-xl border border-glass relative overflow-hidden group">
                          <div className="absolute top-0 left-0 w-1 h-full bg-secondary" />
                          <span className="text-[10px] text-muted font-bold uppercase block mb-1 tracking-widest">Avg Latency</span>
                          <span className="text-3xl font-black gradient-text">{(cinemaData?.metrics?.latency_avg ?? 0).toFixed(0)}<span className="text-sm font-normal text-muted ml-0.5">ms</span></span>
                       </div>
                       <div className="p-5 bg-surface rounded-xl border border-glass relative overflow-hidden group">
                          <div className="absolute top-0 left-0 w-1 h-full bg-accent" />
                          <span className="text-[10px] text-muted font-bold uppercase block mb-1 tracking-widest">Token Usage</span>
                          <span className="text-3xl font-black gradient-text">{cinemaData?.metrics?.token_count ?? 0}</span>
                       </div>
                    </div>
                     <div className="flex flex-col gap-8">
                        {cinemaData?.artifacts?.map((a: any) => (
                           <ArtifactView key={a.id} artifact={a} />
                        ))}
                        {(!cinemaData || !cinemaData?.artifacts || cinemaData?.artifacts?.length === 0) && (
                           <div className="p-12 text-center border-2 border-dashed border-glass rounded-2xl">
                              <p className="text-muted">No artifacts generated yet. Start an agent to see execution results.</p>
                           </div>
                        )}
                     </div>
                 </div>
              )}

              {activeModule === 'hitl' && (
                 <div className="h-full flex items-center justify-center text-center p-12">
                    <div>
                       <ShieldCheck size={48} className="mx-auto mb-4 text-muted opacity-20" />
                       <h3 className="text-lg font-bold mb-2 text-slate-300">HITL Center</h3>
                       <p className="text-sm text-muted max-w-sm">Human-in-the-loop interactions will appear here when an agent requires approval or feedback.</p>
                    </div>
                 </div>
              )}
              {activeModule === 'generation' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', height: '100%' }}>
                  <div style={{ 
                    flex: 1.5, 
                    background: 'var(--bg-surface)', 
                    borderRadius: 'var(--border-radius-lg)', 
                    border: '1px solid var(--glass-border)', 
                    position: 'relative', 
                    display: 'flex', 
                    flexDirection: 'column',
                    alignItems: 'center', 
                    justifyContent: 'center',
                    overflow: 'hidden',
                    backgroundSize: '30px 30px',
                    backgroundImage: 'radial-gradient(circle, rgba(255,255,255,0.03) 1px, transparent 1px)'
                  }}>
                    <div className="flex flex-col items-center gap-6 py-12">
                      {/* Interactive Graph Flow */}
                      <div className="flex flex-col items-center group">
                        <div style={{ width: 80, height: 32, border: '2px solid var(--glass-border)', borderRadius: 16, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.65rem', color: 'var(--text-muted)', fontWeight: 800, letterSpacing: '0.1em' }}>INIT</div>
                        <div style={{ width: 2, height: 24, background: 'linear-gradient(to bottom, var(--glass-border), var(--primary))' }} />
                      </div>

                      <div className="flex flex-col items-center gap-4">
                        {(() => {
                           // Extract nodes from steps (e.g., "Executing Node: Analyzer")
                           const nodeSteps = steps.filter(s => s.text.includes('Node:'));
                           if (nodeSteps.length === 0) {
                             return (
                                <motion.div 
                                  animate={{ opacity: [0.4, 1, 0.4] }} 
                                  transition={{ duration: 2, repeat: Infinity }}
                                  style={{ padding: '1.2rem 2.5rem', background: 'rgba(139, 92, 246, 0.05)', border: '1px solid var(--primary)', borderRadius: 12, color: 'var(--primary)', fontWeight: 600, fontSize: '0.8rem' }}
                                >
                                  ARCHITECTING GRAPH...
                                </motion.div>
                             );
                           }

                           return nodeSteps.map((s, idx) => {
                             const nodeName = s.text.split('Node:')[1].trim();
                             const isCurrent = idx === nodeSteps.length - 1 && !showReport;
                             
                             return (
                               <React.Fragment key={idx}>
                                  <motion.div 
                                    initial={{ opacity: 0, y: 10, scale: 0.9 }}
                                    animate={{ opacity: 1, y: 0, scale: 1 }}
                                    style={{ 
                                      padding: '1rem 2rem', 
                                      background: isCurrent ? 'rgba(139, 92, 246, 0.15)' : 'rgba(255, 255, 255, 0.03)', 
                                      border: `1px solid ${isCurrent ? 'var(--primary)' : 'var(--glass-border)'}`, 
                                      borderRadius: 16, 
                                      boxShadow: isCurrent ? '0 0 30px var(--primary-glow)' : 'none',
                                      color: isCurrent ? '#fff' : 'var(--text-secondary)', 
                                      fontWeight: 700,
                                      display: 'flex',
                                      alignItems: 'center',
                                      gap: '0.75rem',
                                      transition: 'all 0.3s'
                                    }}
                                  >
                                    <div className={isCurrent ? 'spin' : ''}>
                                      <s.icon size={16} color={isCurrent ? 'var(--primary)' : 'var(--text-muted)'} />
                                    </div>
                                    <span style={{ fontSize: '0.9rem', letterSpacing: '0.05em' }}>{nodeName.toUpperCase()}</span>
                                  </motion.div>
                                  {idx < nodeSteps.length - 1 || !showReport ? (
                                    <div style={{ width: 2, height: 24, background: isCurrent ? 'var(--primary)' : 'var(--glass-border)', opacity: 0.5 }} />
                                  ) : (
                                    <motion.div 
                                      initial={{ opacity: 0 }}
                                      animate={{ opacity: 1 }}
                                      className="flex flex-col items-center"
                                    >
                                      <div style={{ width: 2, height: 24, background: 'linear-gradient(to bottom, var(--glass-border), var(--success))' }} />
                                      <div style={{ width: 80, height: 32, border: '2px solid var(--success)', borderRadius: 16, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.65rem', color: 'var(--success)', fontWeight: 800, letterSpacing: '0.1em', boxShadow: '0 0 15px rgba(16, 185, 129, 0.2)' }}>FINALIZED</div>
                                    </motion.div>
                                  )}
                               </React.Fragment>
                             );
                           });
                        })()}
                      </div>
                    </div>
                  </div>
                  <div style={{ flex: 1, background: 'var(--bg-card)', borderRadius: 'var(--border-radius-lg)', border: '1px solid var(--glass-border)', padding: '1.5rem', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                     <h3 style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '1rem' }}>Activity Stream</h3>
                      <div style={{ flex: 1, overflowY: 'auto' }}>
                        {steps.map((step, i) => {
                          const isLast = i === steps.length - 1;
                          const isExecuting = step.text.includes('Executing');
                          return (
                            <div key={i} className={`flex items-center justify-between py-3 border-b border-white/5 ${isLast ? 'bg-primary/5 -mx-4 px-4' : ''}`}>
                               <div className="flex items-center gap-4">
                                  <div className={`p-1.5 rounded-md ${isLast ? 'bg-primary/20' : 'bg-white/5'}`}>
                                    <step.icon size={14} className={isExecuting ? 'spin' : ''} color={isLast ? "var(--primary)" : "var(--text-muted)"} />
                                  </div>
                                  <span className={`text-[13px] font-mono tracking-tight ${isLast ? 'text-white font-bold' : 'text-slate-400'}`}>
                                    {isExecuting && <span className="text-primary mr-1">&gt;</span>}
                                    {step.text}
                                  </span>
                               </div>
                               <span className="text-[10px] font-mono text-muted opacity-40">{step.time}</span>
                            </div>
                          );
                        })}
                      </div>
                      {showReport && (
                        <motion.div 
                          initial={{ opacity: 0, y: 10, scale: 0.95 }}
                          animate={{ opacity: 1, y: 0, scale: 1 }}
                          className="mt-4 p-5 rounded-2xl bg-gradient-to-br from-primary/20 to-secondary/20 border border-primary/30 shadow-2xl shadow-primary/10"
                        >
                          <div className="flex items-center justify-between mb-3">
                             <div className="flex items-center gap-2">
                                <Zap size={14} className="text-primary fill-primary" />
                                <span className="text-[10px] font-black text-primary uppercase tracking-[0.2em]">Agent Execution Complete</span>
                             </div>
                             <button 
                               onClick={() => setActiveModule('cinema')}
                               className="px-4 py-1.5 bg-white text-black text-[10px] font-black rounded-full uppercase tracking-widest hover:scale-105 transition-transform shadow-lg"
                             >
                               View Artifacts
                             </button>
                          </div>
                          <div className="p-3 bg-black/20 rounded-xl border border-white/5">
                             <p className="text-xs font-mono text-slate-200 leading-relaxed italic">"{String(finalReport)}"</p>
                          </div>
                        </motion.div>
                      )}
                     <DataModule />
                  </div>
                </div>
              )}
            </motion.div>
          </AnimatePresence>
        </div>
      </main>

      <style>{`
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { 100% { transform: rotate(360deg); } }
        .gradient-text { background: linear-gradient(135deg, var(--primary), var(--secondary)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
      `}</style>
    </div>
  );
};

export default App;
