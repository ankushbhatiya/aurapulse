"use client";
import { useState, useEffect, useRef } from 'react';
import { useTheme } from "next-themes";
import { minidenticon } from 'minidenticons';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Legend } from 'recharts';
import { Moon, Sun, Zap, Play, FileText, BarChart3, AlertTriangle, RotateCcw, History, Square, Users, Database, Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

export default function Home() {
  const [feedA, setFeedA] = useState<any[]>([]);
  const [feedB, setFeedB] = useState<any[]>([]);
  const [reportA, setReportA] = useState<any>(null);
  const [reportB, setReportB] = useState<any>(null);
  const [postA, setPostA] = useState("");
  const [postB, setPostB] = useState("");
  const [agentCount, setAgentCount] = useState(20);
  const [totalExpected, setTotalExpected] = useState(40);
  const [isSimulating, setIsSimulating] = useState(false);
  const [simulationStatusMsg, setSimulationStatusMsg] = useState<string | null>(null);
  const [activeSimId, setActiveSimId] = useState<string | null>(null);
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);
  const [isIngesting, setIsIngesting] = useState(false);
  const [showIngestDialog, setShowIngestDialog] = useState(false);
  const [isConnected, setIsConnected] = useState(true);
  const [ingestText, setIngestText] = useState("");
  const [history, setHistory] = useState<any[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [sessionId, setSessionId] = useState<string>("");
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  
  // Ref to track if initial load is done to prevent overwriting with defaults
  const isInitialLoadDone = useRef(false);

  // 1. Initial Mount & Health Check
  useEffect(() => {
    setMounted(true);

    // Connectivity Polling
    const checkHealth = async () => {
      try {
        const res = await fetch("http://localhost:8000/health");
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
        const res = await fetch(`http://localhost:8000/draft/${sid}`);
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

    const eventSource = new EventSource("http://localhost:8000/stream");
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === "status") {
          setSimulationStatusMsg(data.message);
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
      clearInterval(healthInterval);
    };
  }, []);

  // 2. Auto-trigger report when simulation finishes
  useEffect(() => {
    if (!isSimulating || !activeSimId || isGeneratingReport || reportA) return;

    const isFinishedA = feedA.length >= totalExpected && totalExpected > 0;
    const isFinishedB = feedB.length >= totalExpected && totalExpected > 0;

    if (isFinishedA && isFinishedB) {
      console.log(`Simulation ${activeSimId} finished (${feedA.length}/${totalExpected}). Auto-triggering reports...`);
      setIsSimulating(false);
      fetchReports(false);
    }
  }, [feedA.length, feedB.length, totalExpected, isSimulating, activeSimId, isGeneratingReport, reportA]);

  // 3. Debounced Auto-Save to Backend
  useEffect(() => {
    if (!mounted || !isInitialLoadDone.current || !sessionId) return;

    const timeoutId = setTimeout(async () => {
      try {
        await fetch("http://localhost:8000/draft", {
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

  const fetchHistory = async () => {
    try {
      const res = await fetch("http://localhost:8000/simulations");
      const data = await res.json();
      setHistory(data);
    } catch (e) {
      console.error("Failed to fetch history", e);
    }
  };

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
      const res = await fetch("http://localhost:8000/simulate", {
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

  const stopSimulation = async () => {
    if (!activeSimId) return;
    try {
      await fetch(`http://localhost:8000/stop/${activeSimId}`, { method: "POST" });
      setIsSimulating(false);
      setSimulationStatusMsg("Simulation Interrupted.");
      fetchHistory();
    } catch (e) {
      console.error("Stop failed", e);
    }
  };

  const loadPastSim = async (sim: any) => {
    setActiveSimId(sim.id);
    
    // Setting these will trigger the auto-save effect, saving this as the new draft
    setPostA(sim.postA || "");
    setPostB(sim.postB || "");
    const loadedCount = parseInt(sim.agent_count || "20");
    setAgentCount(loadedCount);
    
    setTotalExpected(loadedCount * 2);
    setIsSimulating(false);
    setShowHistory(false);
    setReportA(null);
    setReportB(null);
    
    try {
      const [resA, resB] = await Promise.all([
        fetch(`http://localhost:8000/history/${sim.id}/TrackA`),
        fetch(`http://localhost:8000/history/${sim.id}/TrackB`)
      ]);
      const dataA = await resA.json();
      const dataB = await resB.json();
      console.log(`Loaded history for ${sim.id}:`, { dataA, dataB });
      setFeedA(Array.isArray(dataA) ? dataA.reverse() : []);
      setFeedB(Array.isArray(dataB) ? dataB.reverse() : []);

      // Fetch reports for this past simulation
      const [repResA, repResB] = await Promise.all([
        fetch(`http://localhost:8000/report/${sim.id}/TrackA`),
        fetch(`http://localhost:8000/report/${sim.id}/TrackB`)
      ]);
      if (repResA.ok) {
        const ra = await repResA.json();
        console.log("Loaded report A:", ra);
        setReportA(ra);
      }
      if (repResB.ok) {
        const rb = await repResB.json();
        console.log("Loaded report B:", rb);
        setReportB(rb);
      }
    } catch (e) {
      console.error("Failed to load past sim history", e);
    }
  };

  const fetchReports = async (forceRefresh = false) => {
    if (!activeSimId) return;
    console.log(`fetchReports triggered: forceRefresh=${forceRefresh}, activeSimId=${activeSimId}`);
    setIsGeneratingReport(true);
    setSimulationStatusMsg("Generating Analysis...");
    try {
      const urlA = `http://localhost:8000/report/${activeSimId}/TrackA?force_refresh=${forceRefresh}`;
      const urlB = `http://localhost:8000/report/${activeSimId}/TrackB?force_refresh=${forceRefresh}`;
      console.log(`Fetching reports from: ${urlA} and ${urlB}`);
      
      const [resA, resB] = await Promise.all([
        fetch(urlA),
        fetch(urlB)
      ]);

      if (resA.ok) {
        const dataA = await resA.json();
        console.log("Report A Data:", dataA);
        setReportA(dataA);
      }
      if (resB.ok) {
        const dataB = await resB.json();
        console.log("Report B Data:", dataB);
        setReportB(dataB);
      }
    } catch (e) {
      console.error("Report fetch failed", e);
    } finally {
      setIsGeneratingReport(false);
      setSimulationStatusMsg(null);
    }
  };

  const handleIngest = async () => {
    if (!ingestText) return;
    setIsIngesting(true);
    try {
      const res = await fetch("http://localhost:8000/ingest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: ingestText }),
      });
      if (res.ok) {
        setIngestText("");
        setShowIngestDialog(false);
        // Maybe a subtle toast notification later, but alert for now
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
    
    // Delete backend draft
    if (sessionId) {
      try {
        await fetch(`http://localhost:8000/draft/${sessionId}`, { method: "DELETE" });
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
            {activeSimId ? `SESSION: ${activeSimId}` : "SYSTEM_READY"} // OASIS v1.4
          </p>
        </div>
        <div className="flex items-center gap-4">
           {/* Ingestion Trigger */}
           <Dialog open={showIngestDialog} onOpenChange={setShowIngestDialog}>
             <DialogTrigger render={
               <button className="p-2.5 rounded-xl bg-secondary hover:bg-purple-track/10 hover:text-purple-track transition-all border border-border shadow-sm flex items-center gap-2 cursor-pointer">
                 <Database className="h-5 w-5" />
                 <span className="text-xs font-bold uppercase hidden md:inline">Grounding</span>
               </button>
             } />
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
        {/* Left: Setup */}
        <section className="lg:col-span-4 space-y-6">
          <div className="glass-panel p-6 border-pulse/20 shadow-xl">
            <h2 className="text-sm font-bold uppercase tracking-widest text-muted-foreground mb-8 flex items-center gap-2">
              <Zap className="h-4 w-4 text-pulse fill-pulse" />
              1. A/B Configuration
            </h2>
            
            <div className="space-y-6">
              <div className="space-y-4">
                <textarea 
                  className="w-full h-24 bg-background/50 border border-border rounded-xl p-4 text-xs focus:outline-none focus:border-pulse/50 transition-all resize-none font-mono" 
                  placeholder="Post A (Baseline)"
                  value={postA}
                  onChange={(e) => setPostA(e.target.value)}
                />
                <textarea 
                  className="w-full h-24 bg-background/50 border border-border rounded-xl p-4 text-xs focus:outline-none focus:border-pulse/50 transition-all resize-none font-mono" 
                  placeholder="Post B (Variant)"
                  value={postB}
                  onChange={(e) => setPostB(e.target.value)}
                />
              </div>

              <div className="p-4 bg-secondary/30 rounded-xl border border-border">
                 <div className="flex justify-between items-center mb-4">
                    <label className="text-[10px] font-black uppercase tracking-widest text-muted-foreground flex items-center gap-2">
                       <Users className="h-3 w-3 text-pulse" /> Swarm Size
                    </label>
                    <span className="text-xs font-mono text-pulse font-bold">{agentCount} Agents</span>
                 </div>
                 <div className="px-2">
                   <input 
                     type="range" min="5" max="500" step="5"
                     value={agentCount}
                     onChange={(e) => setAgentCount(parseInt(e.target.value))}
                     className="w-full accent-pulse h-1 bg-background rounded-full appearance-none cursor-pointer py-4"
                   />
                 </div>
                 <div className="flex justify-between mt-2 opacity-30 text-[8px] font-bold uppercase tracking-tighter">
                    <span>Sparse</span>
                    <span>Dense Swarm</span>
                 </div>
              </div>
              
              <div className="flex gap-3 pt-2">
                {!isSimulating ? (
                  <button 
                    onClick={handleSimulate}
                    disabled={!postA || !postB}
                    className="flex-grow bg-pulse text-background font-black py-4 rounded-xl transition-all active:scale-[0.98] disabled:opacity-30 flex items-center justify-center gap-2 shadow-lg shadow-pulse/20"
                  >
                    <Play className="h-4 w-4 fill-current" />
                    <span className="uppercase tracking-tighter font-bold">Initialize Deployment</span>
                  </button>
                ) : (
                  <button 
                    onClick={stopSimulation}
                    className="flex-grow bg-neon-red text-white font-black py-4 rounded-xl transition-all active:scale-[0.98] flex items-center justify-center gap-2 shadow-lg shadow-neon-red/20"
                  >
                    <Square className="h-4 w-4 fill-current" />
                    <span className="uppercase tracking-tighter font-bold text-sm">Interrupt Signal</span>
                  </button>
                )}
              </div>
            </div>
          </div>

          <div className="glass-panel p-6 border-dashed border-border/50 bg-transparent flex items-center justify-between">
             <div>
                <h3 className="text-[10px] font-bold uppercase text-muted-foreground mb-1 tracking-widest opacity-60">Engine Capacity</h3>
                <p className="text-xs text-muted-foreground/80 font-medium">
                  {simulationStatusMsg || (isSimulating ? "High Concurrency Execution" : "Awaiting Configuration")}
                </p>
             </div>
             <div className={`h-2 w-2 rounded-full ${isSimulating || isGeneratingReport ? 'bg-pulse animate-pulse' : 'bg-zinc-700'}`} />
          </div>
        </section>
        
        {/* Center: Dual Feed */}
        <section className="lg:col-span-5 flex flex-col h-[75vh]">
          <div className="glass-panel flex-grow flex flex-col overflow-hidden border-pulse/10 shadow-2xl">
            <div className="p-4 border-b border-border flex justify-between items-center bg-muted/20">
              <h2 className="text-sm font-bold uppercase tracking-widest text-purple-track flex items-center gap-2">
                <span className="h-4 w-1 bg-purple-track rounded-full" />
                2. Real-Time Swarm
              </h2>
              {isSimulating && <span className="text-[10px] font-mono text-pulse animate-pulse">STREAMING_ACTIVE</span>}
            </div>
            
            <div className="flex-grow grid grid-cols-2 divide-x divide-border overflow-hidden">
               {/* Track A */}
               <div className="flex flex-col overflow-hidden bg-background/5">
                 <div className="px-4 py-2 bg-muted/10 border-b border-border flex justify-between items-center">
                    <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-widest">Track A</span>
                    <span className="text-[9px] font-mono text-pulse/60">{feedA.length}/{totalExpected}</span>
                 </div>
                 <div className="flex-grow p-4 overflow-y-auto space-y-4 custom-scrollbar">
                    {feedA.map((msg, i) => (
                      <div key={i} className="animate-in fade-in slide-in-from-left-2 duration-300">
                        <div className="flex items-center gap-2 mb-1">
                           <img 
                             src={`data:image/svg+xml;utf8,${encodeURIComponent(minidenticon(msg.persona_name))}`} 
                             alt={msg.persona_name} 
                             className="h-5 w-5 rounded-md bg-white/5 p-0.5 border border-white/10" 
                           />
                           <span className={`text-[9px] font-black uppercase tracking-tight ${msg.bias === 'Hater' ? 'text-neon-red' : 'text-pulse'}`}>{msg.persona_name}</span>
                           {msg.reply_to && <span className="text-[8px] opacity-20">→ {msg.reply_to}</span>}
                        </div>
                        <p className="text-xs text-foreground/80 leading-snug font-mono italic pl-2 border-l border-pulse/20">{msg.comment}</p>
                      </div>
                    ))}
                 </div>
               </div>

               {/* Track B */}
               <div className="flex flex-col overflow-hidden bg-background/5">
                 <div className="px-4 py-2 bg-muted/10 border-b border-border flex justify-between items-center">
                    <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-widest">Track B</span>
                    <span className="text-[9px] font-mono text-pulse/60">{feedB.length}/{totalExpected}</span>
                 </div>
                 <div className="flex-grow p-4 overflow-y-auto space-y-4 custom-scrollbar">
                    {feedB.map((msg, i) => (
                      <div key={i} className="animate-in fade-in slide-in-from-right-2 duration-300">
                        <div className="flex items-center gap-2 mb-1">
                           <img 
                             src={`data:image/svg+xml;utf8,${encodeURIComponent(minidenticon(msg.persona_name))}`} 
                             alt={msg.persona_name} 
                             className="h-5 w-5 rounded-md bg-white/5 p-0.5 border border-white/10" 
                           />
                           <span className={`text-[9px] font-black uppercase tracking-tight ${msg.bias === 'Hater' ? 'text-neon-red' : 'text-pulse'}`}>{msg.persona_name}</span>
                           {msg.reply_to && <span className="text-[8px] opacity-20">→ {msg.reply_to}</span>}
                        </div>
                        <p className="text-xs text-foreground/80 leading-snug font-mono italic pl-2 border-l border-purple-track/20">{msg.comment}</p>
                      </div>
                    ))}
                 </div>
               </div>
            </div>
          </div>
        </section>

        {/* Right: Analytics */}
        <section className="lg:col-span-3 space-y-6 flex flex-col h-[75vh]">
          <div className="glass-panel p-6 border-neon-red/10 shadow-xl flex-grow overflow-y-auto custom-scrollbar">
            <h2 className="text-sm font-bold uppercase tracking-widest text-neon-red mb-8 flex items-center gap-2">
              <BarChart3 className="h-4 w-4" />
              3. Predictive ROI
            </h2>
            
            {(feedA.length > 0 || feedB.length > 0) && (
              <div className="flex flex-col gap-2 mb-8">
                {!reportA ? (
                  <button 
                    onClick={() => fetchReports(false)}
                    disabled={isGeneratingReport}
                    className="w-full bg-secondary border border-border p-4 rounded-xl text-xs font-bold uppercase tracking-widest hover:bg-secondary/80 transition-all flex items-center justify-center gap-2"
                  >
                    <FileText className={`h-4 w-4 ${isGeneratingReport ? 'animate-bounce' : ''}`} />
                    {isGeneratingReport ? "Processing Swarm Data..." : "Generate Analysis"}
                  </button>
                ) : (
                  <button 
                    onClick={() => fetchReports(true)}
                    disabled={isGeneratingReport}
                    className="w-full bg-secondary/20 border border-border/50 p-2 rounded-lg text-[9px] font-bold uppercase tracking-widest hover:bg-secondary/40 transition-all flex items-center justify-center gap-2 opacity-60 hover:opacity-100"
                  >
                    <RotateCcw className={`h-3 w-3 ${isGeneratingReport ? 'animate-spin' : ''}`} />
                    {isGeneratingReport ? "Re-Analyzing..." : "Regenerate Analysis"}
                  </button>
                )}
              </div>
            )}

            {!(reportA && reportB) ? (
              <div className="space-y-10 py-10 opacity-30 text-center">
                 <div className="relative h-24 w-24 mx-auto mb-6">
                    <div className="absolute inset-0 border-2 border-muted rounded-full" />
                    <div className="absolute inset-0 border-2 border-pulse rounded-full border-t-transparent animate-[spin_4s_linear_infinite]" />
                 </div>
                 <p className="text-[10px] uppercase tracking-widest font-bold">Awaiting Data</p>
              </div>
            ) : (
              <div className="space-y-8 animate-in fade-in duration-700">
                 <div className="grid grid-cols-2 gap-4 text-center">
                    <div className="p-3 bg-pulse/5 border border-pulse/20 rounded-xl">
                       <span className="text-[8px] font-black text-pulse/60 uppercase block mb-1">Track A Score</span>
                       <div className="text-2xl font-black text-pulse">{reportA?.confidence_score}%</div>
                    </div>
                    <div className="p-3 bg-purple-track/5 border border-purple-track/20 rounded-xl">
                       <span className="text-[8px] font-black text-purple-track/60 uppercase block mb-1">Track B Score</span>
                       <div className="text-2xl font-black text-purple-track">{reportB?.confidence_score}%</div>
                    </div>
                 </div>
                 <div className="p-4 bg-neon-red/5 border border-neon-red/20 rounded-xl">
                    <div className="flex items-center gap-2 mb-2 uppercase text-[9px] font-black text-neon-red">
                       <AlertTriangle className="h-3 w-3" /> Risk Insight
                    </div>
                    <p className="text-[10px] text-zinc-400 font-mono italic leading-relaxed">{reportB?.top_risk_factor || reportA?.top_risk_factor}</p>
                 </div>
                 <div className="space-y-6">
                    {[
                      { label: "Viral Momentum", valA: reportA?.viral_momentum, valB: reportB?.viral_momentum },
                      { label: "Controversy Risk", valA: reportA?.controversy_risk, valB: reportB?.controversy_risk },
                      { label: "Community Drift", valA: reportA?.community_drift, valB: reportB?.community_drift }
                    ].map((item) => (
                      <div key={item.label} className="space-y-3">
                        <div className="flex justify-between text-[9px] font-black uppercase text-muted-foreground tracking-widest mb-1">
                          <span>{item.label}</span>
                        </div>

                        {/* Track A Bar */}
                        <div className="space-y-1">
                          <div className="flex justify-between items-center px-1">
                            <span className="text-[7px] font-bold text-pulse/80 uppercase">Track A</span>
                            <span className="text-[8px] font-mono text-pulse">{item.valA}%</span>
                          </div>
                          <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
                            <div style={{ width: `${item.valA || 0}%` }} className={`h-full bg-pulse shadow-[0_0_8px_rgba(0,246,255,0.2)]`} />
                          </div>
                        </div>

                        {/* Track B Bar */}
                        <div className="space-y-1">
                          <div className="flex justify-between items-center px-1">
                            <span className="text-[7px] font-bold text-purple-track/80 uppercase">Track B</span>
                            <span className="text-[8px] font-mono text-purple-track">{item.valB}%</span>
                          </div>
                          <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden">
                            <div style={{ width: `${item.valB || 0}%` }} className={`h-full bg-purple-track shadow-[0_0_8px_rgba(100,255,218,0.2)]`} />
                          </div>
                        </div>
                      </div>
                    ))}
                 </div>
              </div>
            )}
          </div>
        </section>
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
                       <span className="text-[10px] font-black text-muted-foreground uppercase flex items-center gap-1">
                         View Deck <Play className="h-2 w-2 fill-current" />
                       </span>
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
