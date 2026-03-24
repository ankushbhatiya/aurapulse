"use client";
import { useState, useEffect, useRef, useCallback } from 'react';
import { useTheme } from "next-themes";
import { Moon, Sun, RotateCcw, History, Database, Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { ControlPanel } from '@/components/simulation/ControlPanel';
import { SimulationFeed, type SimulationMessage } from '@/components/simulation/SimulationFeed';
import { AnalyticsDashboard, type SimulationReport } from '@/components/simulation/AnalyticsDashboard';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface SimulationHistoryItem {
  id: string;
  timestamp: string;
  postA: string;
  postB: string;
  status: string;
  agent_count: string;
}

export default function Home() {
  const [feedA, setFeedA] = useState<SimulationMessage[]>([]);
  const [feedB, setFeedB] = useState<SimulationMessage[]>([]);
  const [reportA, setReportA] = useState<SimulationReport | null>(null);
  const [reportB, setReportB] = useState<SimulationReport | null>(null);
  const [postA, setPostA] = useState("");
  const [postB, setPostB] = useState("");
  const [agentCount, setAgentCount] = useState(10);
  const [totalExpected, setTotalExpected] = useState(20);
  const [isSimulating, setIsSimulating] = useState(false);
  const [simulationStatusMsg, setSimulationStatusMsg] = useState<string | null>(null);
  const [activeSimId, setActiveSimId] = useState<string | null>(null);
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);
  const [isIngesting, setIsIngesting] = useState(false);
  const [showIngestDialog, setShowIngestDialog] = useState(false);
  const [isConnected, setIsConnected] = useState(true);
  const [ingestText, setIngestText] = useState("");
  const [history, setHistory] = useState<SimulationHistoryItem[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [sessionId, setSessionId] = useState<string>("");
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  
  // Ref to track if initial load is done to prevent overwriting with defaults
  const isInitialLoadDone = useRef(false);

  const fetchHistory = useCallback(async () => {
    try {
      const res = await fetch(`${BASE_URL}/simulations`);
      const data = await res.json();
      setHistory(data);
    } catch (e) {
      console.error("Failed to fetch history", e);
    }
  }, []);

  const fetchReports = useCallback(async (forceRefresh = false) => {
    if (!activeSimId) return;
    setIsGeneratingReport(true);
    setSimulationStatusMsg("Generating Analysis...");
    try {
      const urlA = `${BASE_URL}/report/${activeSimId}/TrackA?force_refresh=${forceRefresh}`;
      const urlB = `${BASE_URL}/report/${activeSimId}/TrackB?force_refresh=${forceRefresh}`;
      
      const [resA, resB] = await Promise.all([fetch(urlA), fetch(urlB)]);

      if (resA.ok) setReportA(await resA.json());
      if (resB.ok) setReportB(await resB.json());
    } catch (e) {
      console.error("Report fetch failed", e);
    } finally {
      setIsGeneratingReport(false);
      setSimulationStatusMsg(null);
    }
  }, [activeSimId]);

  // 1. Initial Mount & Health Check
  useEffect(() => {
    setMounted(true);

    // Connectivity Polling
    const checkHealth = async () => {
      try {
        const res = await fetch(`${BASE_URL}/health`);
        setIsConnected(res.ok);
      } catch (e) {
        setIsConnected(false);
      }
    };
    const healthInterval = setInterval(checkHealth, 5000);
    checkHealth();
    
    // Initialize or retrieve Session ID
    let currentSessionId = localStorage.getItem("aurapulse_session_id");
    if (!currentSessionId) {
      currentSessionId = crypto.randomUUID();
      localStorage.setItem("aurapulse_session_id", currentSessionId);
    }
    setSessionId(currentSessionId);

    // Fetch initial draft from backend
    const loadDraft = async (sid: string) => {
      try {
        const res = await fetch(`${BASE_URL}/draft/${sid}`);
        const draft = await res.json();
        if (draft) {
          setPostA(draft.postA || "");
          setPostB(draft.postB || "");
          if (draft.agent_count) setAgentCount(draft.agent_count);
        }
      } catch (e) {
        console.error("Failed to load backend draft", e);
      } finally {
        isInitialLoadDone.current = true;
      }
    };
    
    loadDraft(currentSessionId);
    fetchHistory();

    return () => {
      clearInterval(healthInterval);
    };
  }, [fetchHistory]);

  // 2. Stream Management
  useEffect(() => {
    if (!mounted) return;

    const streamUrl = activeSimId ? `${BASE_URL}/stream?sim_id=${activeSimId}` : `${BASE_URL}/stream`;
    const eventSource = new EventSource(streamUrl);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === "status") {
          // If we are filtering by sim_id, we only care about status messages for that sim (or all if no activeSimId)
          if (!activeSimId || data.simulation_id === activeSimId) {
            setSimulationStatusMsg(data.message);
          }
          return;
        }

        if (data.total_expected) {
          setTotalExpected(prev => Math.max(prev, data.total_expected));
        }
        
        if (data.track_id === "TrackA") {
          setFeedA((prev) => [data, ...prev].slice(0, 1000));
        } else if (data.track_id === "TrackB") {
          setFeedB((prev) => [data, ...prev].slice(0, 1000));
        }
      } catch (e) {
        console.error("Error parsing SSE data", e);
      }
    };

    return () => {
      eventSource.close();
    };
  }, [activeSimId, mounted]);

  // 3. Auto-trigger report when simulation finishes
  useEffect(() => {
    if (!isSimulating || !activeSimId || isGeneratingReport || reportA) return;

    const isFinishedA = feedA.length >= totalExpected && totalExpected > 0;
    const isFinishedB = feedB.length >= totalExpected && totalExpected > 0;

    if (isFinishedA && isFinishedB) {
      console.log(`Simulation ${activeSimId} finished (${feedA.length}/${totalExpected}). Auto-triggering reports...`);
      setIsSimulating(false);
      fetchReports(false);
    }
  }, [feedA.length, feedB.length, totalExpected, isSimulating, activeSimId, isGeneratingReport, reportA, fetchReports]);

  // 3. Debounced Auto-Save to Backend
  useEffect(() => {
    if (!mounted || !isInitialLoadDone.current || !sessionId) return;

    const timeoutId = setTimeout(async () => {
      try {
        await fetch(`${BASE_URL}/draft`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: sessionId,
            postA: postA,
            postB: postB,
            agent_count: agentCount
          }),
        });
      } catch (e) {
        console.error("Failed to save draft to backend", e);
      }
    }, 500); // 500ms debounce

    return () => clearTimeout(timeoutId);
  }, [postA, postB, agentCount, sessionId, mounted]);

  const handleSimulate = async () => {
    if (!postA || !postB) return;
    setIsSimulating(true);
    setSimulationStatusMsg("Initializing Swarm Engine...");
    setFeedA([]);
    setFeedB([]);
    setReportA(null);
    setReportB(null);
    setTotalExpected(agentCount * 2); // Default estimate
    try {
      const res = await fetch(`${BASE_URL}/simulate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ postA, postB, agent_count: agentCount }),
      });
      const data = await res.json();
      setActiveSimId(data.simulation_id);
      fetchHistory();
    } catch (e) {
      console.error("Simulate failed", e);
      setIsSimulating(false);
      setSimulationStatusMsg(null);
    }
  };

  const stopSimulation = async (sim_id_to_stop?: string) => {
    const sid = sim_id_to_stop || activeSimId;
    if (!sid) return;
    try {
      await fetch(`${BASE_URL}/stop/${sid}`, { method: "POST" });
      if (!sim_id_to_stop) {
        setIsSimulating(false);
        setSimulationStatusMsg("Simulation Interrupted.");
      }
      fetchHistory();
    } catch (e) {
      console.error("Stop failed", e);
    }
  };

  const loadPastSim = async (sim: SimulationHistoryItem) => {
    setActiveSimId(sim.id);
    setPostA(sim.postA || "");
    setPostB(sim.postB || "");
    const loadedCount = parseInt(sim.agent_count || "10");
    setAgentCount(loadedCount);
    setTotalExpected(loadedCount * 2);
    setIsSimulating(false);
    setShowHistory(false);
    setReportA(null);
    setReportB(null);
    
    try {
      const [resA, resB] = await Promise.all([
        fetch(`${BASE_URL}/history/${sim.id}/TrackA`),
        fetch(`${BASE_URL}/history/${sim.id}/TrackB`)
      ]);
      const dataA = await resA.json();
      const dataB = await resB.json();
      setFeedA(Array.isArray(dataA) ? dataA.reverse() : []);
      setFeedB(Array.isArray(dataB) ? dataB.reverse() : []);

      const [repResA, repResB] = await Promise.all([
        fetch(`${BASE_URL}/report/${sim.id}/TrackA`),
        fetch(`${BASE_URL}/report/${sim.id}/TrackB`)
      ]);
      if (repResA.ok) setReportA(await repResA.json());
      if (repResB.ok) setReportB(await repResB.json());
    } catch (e) {
      console.error("Failed to load past sim history", e);
    }
  };

  const handleIngest = async () => {
    if (!ingestText) return;
    setIsIngesting(true);
    try {
      const res = await fetch(`${BASE_URL}/ingest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: ingestText }),
      });
      if (res.ok) {
        setIngestText("");
        setShowIngestDialog(false);
        alert("Knowledge Graph Updated successfully.");
      }
    } catch (e) {
      console.error("Ingestion failed", e);
    } finally {
      setIsIngesting(false);
    }
  };

  const clearSession = async () => {
    if (isSimulating) stopSimulation();
    setFeedA([]);
    setFeedB([]);
    setReportA(null);
    setReportB(null);
    setPostA("");
    setPostB("");
    setActiveSimId(null);
    
    if (sessionId) {
      try {
        await fetch(`${BASE_URL}/draft/${sessionId}`, { method: "DELETE" });
      } catch (e) {
        console.error("Failed to clear backend draft", e);
      }
    }
  };

  if (!mounted) return null;

  return (
    <main className="min-h-screen bg-background text-foreground p-6 md:p-10 font-sans selection:bg-pulse/30 relative">
      {/* Header */}
      <header className="flex justify-between items-center mb-10">
        <div>
          <h1 className="text-3xl font-black tracking-tighter text-foreground glow-text-pulse uppercase">
            AURAPULSE <span className="text-pulse">GOD VIEW</span>
          </h1>
          <p className="text-muted-foreground text-xs mt-1 font-mono tracking-widest opacity-70 uppercase italic">
            {activeSimId ? `SESSION: ${activeSimId}` : "SYSTEM_READY"} {/* OASIS v1.4 */}
          </p>
        </div>
        <div className="flex items-center gap-4">
           {/* Ingestion Trigger */}
           <Dialog open={showIngestDialog} onOpenChange={setShowIngestDialog}>
             <DialogTrigger asChild>
               <button className="p-2.5 rounded-xl bg-secondary hover:bg-purple-track/10 hover:text-purple-track transition-all border border-border shadow-sm flex items-center gap-2 cursor-pointer">
                 <Database className="h-5 w-5" />
                 <span className="text-xs font-bold uppercase hidden md:inline">Grounding</span>
               </button>
             </DialogTrigger>
             <DialogContent className="sm:max-w-[600px] bg-zinc-950 border-zinc-800 text-white">
               <DialogHeader>
                 <DialogTitle className="text-pulse font-black tracking-widest uppercase">Knowledge Ingestion</DialogTitle>
                 <DialogDescription className="text-zinc-500 font-mono text-xs uppercase opacity-70">
                   Inject raw text into the GraphRAG knowledge base to ground your agent swarm.
                 </DialogDescription>
               </DialogHeader>
               <div className="py-6 space-y-4">
                 <textarea 
                   className="w-full h-64 bg-black border border-zinc-800 rounded-xl p-4 text-sm focus:border-pulse/50 transition-all outline-none font-mono"
                   placeholder="Paste brand guidelines, news articles, or past transcripts here..."
                   value={ingestText}
                   onChange={(e) => setIngestText(e.target.value)}
                 />
                 <button 
                   onClick={handleIngest}
                   disabled={isIngesting || !ingestText}
                   className="w-full bg-pulse text-black font-black py-4 rounded-xl flex items-center justify-center gap-2 disabled:opacity-30"
                 >
                   {isIngesting ? <Loader2 className="h-5 w-5 animate-spin" /> : <Database className="h-5 w-5" />}
                   {isIngesting ? "EXTRACTING ENTITIES..." : "PROCESS & INGEST"}
                 </button>
               </div>
             </DialogContent>
           </Dialog>

           <button 
             onClick={() => setShowHistory(!showHistory)}
             className={`p-2.5 rounded-xl transition-all border border-border shadow-sm flex items-center gap-2 ${showHistory ? 'bg-pulse text-background' : 'bg-secondary hover:bg-secondary/80'}`}
           >
             <History className="h-5 w-5" />
             <span className="text-xs font-bold uppercase hidden md:inline">History</span>
           </button>
           <button 
             onClick={clearSession}
             className="p-2.5 rounded-xl bg-secondary hover:bg-neon-red/10 hover:text-neon-red transition-all border border-border shadow-sm"
             title="Reset Environment"
           >
             <RotateCcw className="h-5 w-5" />
           </button>
           <button 
             onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
             className="p-2.5 rounded-xl bg-secondary hover:bg-secondary/80 transition-all border border-border shadow-sm"
           >
             {theme === "dark" ? <Sun className="h-5 w-5 text-pulse" /> : <Moon className="h-5 w-5 text-primary" />}
           </button>
           <div className={`hidden md:flex items-center gap-3 glass-panel px-4 py-2 border-border/50 ${isConnected ? 'bg-purple-track/5 border-purple-track/20' : 'bg-neon-red/5 border-neon-red/20'}`}>
              <div className={`h-2 w-2 rounded-full ${isConnected ? 'bg-purple-track animate-pulse shadow-[0_0_8px_rgba(100,255,218,0.5)]' : 'bg-neon-red shadow-[0_0_8px_rgba(255,0,85,0.5)]'}`} />
              <span className={`text-[10px] font-mono font-bold uppercase tracking-widest ${isConnected ? 'text-purple-track' : 'text-neon-red'}`}>
                {isConnected ? 'OASIS Link Active' : 'System Offline'}
              </span>
           </div>
        </div>
      </header>
      
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 h-full">
        <ControlPanel 
          postA={postA} setPostA={setPostA}
          postB={postB} setPostB={setPostB}
          agentCount={agentCount} setAgentCount={setAgentCount}
          isSimulating={isSimulating}
          handleSimulate={handleSimulate}
          stopSimulation={stopSimulation}
          simulationStatusMsg={simulationStatusMsg}
          isGeneratingReport={isGeneratingReport}
        />
        
        <SimulationFeed 
          feedA={feedA}
          feedB={feedB}
          totalExpected={totalExpected}
          isSimulating={isSimulating}
        />

        <AnalyticsDashboard 
          reportA={reportA}
          reportB={reportB}
          feedA={feedA}
          feedB={feedB}
          isGeneratingReport={isGeneratingReport}
          fetchReports={fetchReports}
        />
      </div>

      {/* History Sidebar */}
      {showHistory && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-background/80 backdrop-blur-sm" onClick={() => setShowHistory(false)} />
          <aside className="relative w-full max-w-md bg-secondary border-l border-border h-full shadow-2xl p-8 flex flex-col animate-in slide-in-from-right duration-300">
            <div className="flex justify-between items-center mb-8">
              <h2 className="text-xl font-black tracking-tight flex items-center gap-2 uppercase">
                <History className="h-5 w-5 text-pulse" /> History
              </h2>
              <button onClick={() => setShowHistory(false)} className="text-muted-foreground hover:text-foreground">
                <RotateCcw className="h-5 w-5 rotate-45" />
              </button>
            </div>
            
            <div className="flex-grow overflow-y-auto space-y-4 custom-scrollbar pr-2">
              {!Array.isArray(history) || history.length === 0 ? (
                <div className="h-full flex items-center justify-center text-muted-foreground/40 italic text-sm">No recorded deployments found.</div>
              ) : (
                history.map((sim) => (
                  <div 
                    key={sim.id} 
                    onClick={() => loadPastSim(sim)}
                    className={`p-4 rounded-2xl border transition-all cursor-pointer hover:scale-[1.02] ${activeSimId === sim.id ? 'bg-pulse/10 border-pulse' : 'bg-background/40 border-border hover:border-pulse/40'}`}
                  >
                    <div className="flex justify-between items-center mb-3">
                      <span className="text-[10px] font-black uppercase tracking-widest text-pulse">{sim.id}</span>
                      <span className="text-[10px] font-mono opacity-40">{new Date(parseFloat(sim.timestamp) * 1000).toLocaleString()}</span>
                    </div>
                    <div className="space-y-2 mb-4">
                      <p className="text-xs text-zinc-400 line-clamp-1 border-l border-pulse/20 pl-2 italic">A: {sim.postA}</p>
                      <p className="text-xs text-zinc-400 line-clamp-1 border-l border-purple-track/20 pl-2 italic">B: {sim.postB}</p>
                    </div>
                    <div className="flex justify-between items-center">
                       <div className="flex items-center gap-2">
                          <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${sim.status === 'Stopped' ? 'bg-neon-red/10 text-neon-red' : 'bg-purple-track/10 text-purple-track'}`}>
                            {sim.status === 'Stopped' ? 'Interrupted' : 'Deployed'}
                          </span>
                          <span className="text-[10px] font-mono opacity-40">{sim.agent_count} AGENTS</span>
                       </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </aside>
        </div>
      )}
      
      <style jsx global>{`
        .custom-scrollbar::-webkit-scrollbar { width: 3px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: var(--muted); border-radius: 10px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: var(--pulse); }
      `}</style>
    </main>
  );
}
