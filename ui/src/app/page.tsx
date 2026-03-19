"use client";
import { useState, useEffect } from 'react';
import { useTheme } from "next-themes";
import { Moon, Sun, Zap, Play, FileText, BarChart3, AlertTriangle } from "lucide-react";

export default function Home() {
  const [feedA, setFeedA] = useState<any[]>([]);
  const [feedB, setFeedB] = useState<any[]>([]);
  const [reportA, setReportA] = useState<any>(null);
  const [reportB, setReportB] = useState<any>(null);
  const [postA, setPostA] = useState("");
  const [postB, setPostB] = useState("");
  const [isSimulating, setIsSimulating] = useState(false);
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const eventSource = new EventSource("http://localhost:8000/stream");
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.track_id === "TrackA") {
          setFeedA((prev) => [data, ...prev].slice(0, 50));
        } else if (data.track_id === "TrackB") {
          setFeedB((prev) => [data, ...prev].slice(0, 50));
        }
      } catch (e) {
        console.error("Error parsing SSE data", e);
      }
    };
    return () => eventSource.close();
  }, []);

  const handleSimulate = async () => {
    if (!postA || !postB) return;
    setIsSimulating(true);
    setFeedA([]);
    setFeedB([]);
    setReportA(null);
    setReportB(null);
    try {
      await fetch("http://localhost:8000/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ postA, postB }),
      });
    } catch (e) {
      console.error("Simulate failed", e);
    } finally {
      setTimeout(() => setIsSimulating(false), 2000);
    }
  };

  const fetchReports = async () => {
    setIsGeneratingReport(true);
    try {
      const resA = await fetch("http://localhost:8000/report/TrackA");
      const dataA = await resA.json();
      setReportA(dataA);

      const resB = await fetch("http://localhost:8000/report/TrackB");
      const dataB = await resB.json();
      setReportB(dataB);
    } catch (e) {
      console.error("Report fetch failed", e);
    } finally {
      setIsGeneratingReport(false);
    }
  };

  if (!mounted) return null;

  return (
    <main className="min-h-screen bg-background text-foreground p-6 md:p-10 font-sans selection:bg-pulse/30">
      {/* Header */}
      <header className="flex justify-between items-center mb-10">
        <div>
          <h1 className="text-3xl font-black tracking-tighter text-foreground glow-text-pulse">
            AURAPULSE <span className="text-pulse">GOD VIEW</span>
          </h1>
          <p className="text-muted-foreground text-xs mt-1 font-mono tracking-widest opacity-70 uppercase italic">OASIS Engine Active // MiroFish Architecture</p>
        </div>
        <div className="flex items-center gap-6">
           <button 
             onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
             className="p-2.5 rounded-xl bg-secondary hover:bg-secondary/80 transition-all border border-border shadow-sm group"
             aria-label="Toggle theme"
           >
             {theme === "dark" ? <Sun className="h-5 w-5 text-pulse group-hover:rotate-45 transition-transform" /> : <Moon className="h-5 w-5 text-primary" />}
           </button>
           <div className="hidden md:flex items-center gap-3 glass-panel px-4 py-2 border-aquamarine/20 bg-aquamarine/5">
              <div className="h-2 w-2 rounded-full bg-aquamarine animate-pulse" />
              <span className="text-[10px] font-mono text-aquamarine font-bold uppercase tracking-widest">OASIS Link Established</span>
           </div>
        </div>
      </header>
      
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 h-full">
        {/* Left: Setup (4 cols) */}
        <section className="lg:col-span-4 space-y-6">
          <div className="glass-panel p-6 glow-border-pulse transition-all duration-500 hover:shadow-pulse/10 border-pulse/20">
            <h2 className="text-sm font-bold uppercase tracking-widest text-muted-foreground mb-8 flex items-center gap-2">
              <Zap className="h-4 w-4 text-pulse fill-pulse" />
              1. A/B Configuration
            </h2>
            
            <div className="space-y-6">
              <div className="space-y-4">
                <div>
                  <label className="text-[10px] font-bold uppercase text-muted-foreground mb-2 block tracking-widest opacity-60">Post Narrative A (Baseline)</label>
                  <textarea 
                    className="w-full h-28 bg-background/50 border border-border rounded-xl p-4 text-sm focus:outline-none focus:border-pulse/50 transition-all placeholder:text-muted-foreground/30 resize-none font-mono" 
                    placeholder="e.g., Sustainable fashion announcement..."
                    value={postA}
                    onChange={(e) => setPostA(e.target.value)}
                  />
                </div>
                <div>
                  <label className="text-[10px] font-bold uppercase text-muted-foreground mb-2 block tracking-widest opacity-60">Post Narrative B (Variant)</label>
                  <textarea 
                    className="w-full h-28 bg-background/50 border border-border rounded-xl p-4 text-sm focus:outline-none focus:border-pulse/50 transition-all placeholder:text-muted-foreground/30 resize-none font-mono" 
                    placeholder="e.g., Edgy fashion statement..."
                    value={postB}
                    onChange={(e) => setPostB(e.target.value)}
                  />
                </div>
              </div>
              
              <button 
                onClick={handleSimulate}
                disabled={isSimulating || !postA || !postB}
                className="w-full group relative overflow-hidden bg-pulse text-background font-black py-4 rounded-xl transition-all active:scale-[0.98] disabled:opacity-30 disabled:cursor-not-allowed shadow-xl shadow-pulse/20 flex items-center justify-center gap-2"
              >
                <Play className={`h-4 w-4 fill-current ${isSimulating ? 'animate-ping' : ''}`} />
                <span className="relative z-10 uppercase tracking-tighter">{isSimulating ? "Injecting OASIS Swarm..." : "Initialize A/B Simulation"}</span>
              </button>
            </div>
          </div>

          <div className="glass-panel p-6 border-dashed border-border/50 bg-transparent flex items-center justify-between group cursor-help transition-all hover:bg-muted/10">
             <div>
                <h3 className="text-[10px] font-bold uppercase text-muted-foreground mb-1 tracking-widest opacity-60">Persona Model</h3>
                <p className="text-xs text-muted-foreground/80 font-medium">GraphRAG-Grounded Twins</p>
             </div>
             <div className="text-[10px] font-mono bg-secondary px-2 py-1 rounded border border-border group-hover:text-pulse transition-colors uppercase">20 Digital Identities</div>
          </div>
        </section>
        
        {/* Center: Dual Feed (5 cols) */}
        <section className="lg:col-span-5 flex flex-col h-[70vh]">
          <div className="glass-panel flex-grow flex flex-col overflow-hidden border-pulse/10 shadow-2xl">
            <div className="p-4 border-b border-border flex justify-between items-center bg-muted/20">
              <h2 className="text-sm font-bold uppercase tracking-widest text-aquamarine flex items-center gap-2">
                <span className="h-4 w-1 bg-aquamarine rounded-full" />
                2. Live Swarm Feed
              </h2>
              <div className="flex gap-2">
                 <div className="h-1.5 w-1.5 rounded-full bg-pulse animate-pulse" />
                 <div className="h-1.5 w-1.5 rounded-full bg-pulse animate-pulse delay-75" />
                 <div className="h-1.5 w-1.5 rounded-full bg-pulse animate-pulse delay-150" />
              </div>
            </div>
            
            <div className="flex-grow grid grid-cols-2 divide-x divide-border overflow-hidden">
               {/* Track A */}
               <div className="flex flex-col overflow-hidden bg-background/5">
                 <div className="px-4 py-2 bg-muted/10 border-b border-border flex justify-between items-center">
                    <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-widest">Track A (Baseline)</span>
                    <span className="text-[9px] font-mono text-pulse/60">{feedA.length}</span>
                 </div>
                 <div className="flex-grow p-4 overflow-y-auto space-y-4 custom-scrollbar">
                    {feedA.length === 0 && !isSimulating && (
                      <div className="h-full flex items-center justify-center opacity-20 italic text-[10px] font-mono">Awaiting Signal...</div>
                    )}
                    {feedA.map((msg, i) => (
                      <div key={i} className="animate-in fade-in slide-in-from-left-2 duration-300">
                        <div className="flex items-center gap-2 mb-1">
                           <span className={`text-[9px] font-black uppercase tracking-tight ${msg.bias === 'Hater' ? 'text-neon-red' : 'text-pulse'}`}>{msg.persona_name}</span>
                           {msg.reply_to && <span className="text-[8px] opacity-20">→ {msg.reply_to}</span>}
                        </div>
                        <p className="text-xs text-foreground/80 leading-snug font-mono italic pl-2 border-l border-pulse/20 italic">
                          {msg.comment}
                        </p>
                      </div>
                    ))}
                 </div>
               </div>

               {/* Track B */}
               <div className="flex flex-col overflow-hidden bg-background/5">
                 <div className="px-4 py-2 bg-muted/10 border-b border-border flex justify-between items-center">
                    <span className="text-[9px] font-bold text-zinc-500 uppercase tracking-widest">Track B (Variant)</span>
                    <span className="text-[9px] font-mono text-pulse/60">{feedB.length}</span>
                 </div>
                 <div className="flex-grow p-4 overflow-y-auto space-y-4 custom-scrollbar">
                    {feedB.length === 0 && !isSimulating && (
                      <div className="h-full flex items-center justify-center opacity-20 italic text-[10px] font-mono">Awaiting Signal...</div>
                    )}
                    {feedB.map((msg, i) => (
                      <div key={i} className="animate-in fade-in slide-in-from-right-2 duration-300">
                        <div className="flex items-center gap-2 mb-1">
                           <span className={`text-[9px] font-black uppercase tracking-tight ${msg.bias === 'Hater' ? 'text-neon-red' : 'text-pulse'}`}>{msg.persona_name}</span>
                           {msg.reply_to && <span className="text-[8px] opacity-20">→ {msg.reply_to}</span>}
                        </div>
                        <p className="text-xs text-foreground/80 leading-snug font-mono italic pl-2 border-l border-aquamarine/20 italic">
                          {msg.comment}
                        </p>
                      </div>
                    ))}
                 </div>
               </div>
            </div>
          </div>
        </section>

        {/* Right: Analytics (3 cols) */}
        <section className="lg:col-span-3 space-y-6 flex flex-col">
          <div className="glass-panel p-6 border-neon-red/10 shadow-xl flex-grow overflow-y-auto custom-scrollbar">
            <h2 className="text-sm font-bold uppercase tracking-widest text-neon-red mb-8 flex items-center gap-2">
              <BarChart3 className="h-4 w-4" />
              3. Predictive ROI
            </h2>
            
            {(feedA.length > 0 || feedB.length > 0) && !reportA && (
              <button 
                onClick={fetchReports}
                disabled={isGeneratingReport}
                className="w-full bg-secondary border border-border p-4 rounded-xl text-xs font-bold uppercase tracking-widest hover:bg-secondary/80 transition-all flex items-center justify-center gap-2 mb-8"
              >
                <FileText className={`h-4 w-4 ${isGeneratingReport ? 'animate-bounce' : ''}`} />
                {isGeneratingReport ? "Synthesizing Results..." : "Generate Final Report"}
              </button>
            )}

            {!reportA ? (
              <div className="space-y-10 py-10 opacity-30">
                 <div className="relative h-32 w-32 mx-auto">
                    <div className="absolute inset-0 border-4 border-muted rounded-full" />
                    <div className="absolute inset-0 border-4 border-pulse rounded-full border-t-transparent animate-[spin_4s_linear_infinite]" />
                    <div className="absolute inset-0 flex items-center justify-center flex-col">
                      <span className="text-2xl font-black text-foreground">--</span>
                      <span className="text-[8px] font-bold text-muted-foreground uppercase tracking-widest opacity-50">Confidence</span>
                    </div>
                 </div>
                 <p className="text-[10px] text-center uppercase tracking-widest font-bold">Simulate to unlock analytics</p>
              </div>
            ) : (
              <div className="space-y-8 animate-in fade-in duration-700">
                 {/* Comparative Stats */}
                 <div className="grid grid-cols-2 gap-4">
                    <div className="p-3 bg-pulse/5 border border-pulse/20 rounded-xl">
                       <span className="text-[8px] font-black uppercase text-pulse/60 block mb-1">Track A Score</span>
                       <div className="text-2xl font-black text-pulse">{reportA.confidence_score}%</div>
                    </div>
                    <div className="p-3 bg-aquamarine/5 border border-aquamarine/20 rounded-xl">
                       <span className="text-[8px] font-black uppercase text-aquamarine/60 block mb-1">Track B Score</span>
                       <div className="text-2xl font-black text-aquamarine">{reportB.confidence_score}%</div>
                    </div>
                 </div>

                 {/* Risk Factors */}
                 <div className="space-y-4">
                    <div className="p-4 bg-neon-red/5 border border-neon-red/20 rounded-xl">
                       <div className="flex items-center gap-2 mb-2">
                          <AlertTriangle className="h-3 w-3 text-neon-red" />
                          <span className="text-[9px] font-black uppercase text-neon-red">Critical Risk: Track B</span>
                       </div>
                       <p className="text-[10px] leading-relaxed text-zinc-400 font-mono italic">{reportB.top_risk_factor}</p>
                    </div>
                 </div>

                 {/* Progress Bars */}
                 <div className="space-y-6">
                    {[
                      { label: "Viral Momentum", valA: reportA.viral_momentum, valB: reportB.viral_momentum, color: "bg-pulse" },
                      { label: "Controversy Risk", valA: reportA.controversy_risk, valB: reportB.controversy_risk, color: "bg-neon-red" },
                      { label: "Community Drift", valA: reportA.community_drift, valB: reportB.community_drift, color: "bg-aquamarine" }
                    ].map((item) => (
                      <div key={item.label} className="space-y-2">
                        <div className="flex justify-between text-[9px] font-black uppercase text-muted-foreground tracking-widest">
                          <span>{item.label}</span>
                          <span className="font-mono text-pulse">{item.valA}% | {item.valB}%</span>
                        </div>
                        <div className="h-1.5 w-full bg-muted rounded-full overflow-hidden flex">
                          <div style={{ width: `${item.valA}%` }} className={`h-full ${item.color} opacity-40`} />
                          <div style={{ width: `${item.valB}%` }} className={`h-full ${item.color} border-l border-background`} />
                        </div>
                      </div>
                    ))}
                 </div>
              </div>
            )}
          </div>

          <div className="glass-panel p-5 bg-pulse/5 border-pulse/20 relative overflow-hidden mt-6 group">
             <div className="absolute -top-4 -right-4 p-2 opacity-5 group-hover:opacity-20 transition-opacity">
                <BarChart3 className="h-16 w-10 text-pulse" />
             </div>
             <p className="text-[10px] leading-relaxed text-pulse/90 font-mono italic relative z-10">
               {reportA ? reportA.sentiment_summary : "System observing A/B vectors. High-fidelity personas engaged in parallel validation tracks."}
             </p>
          </div>
        </section>
      </div>
      
      <style jsx global>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 3px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: var(--muted);
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: var(--pulse);
        }
      `}</style>
    </main>
  );
}
