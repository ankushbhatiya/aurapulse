"use client";
import { useState, useEffect } from 'react';
import { useTheme } from "next-themes";
import { Moon, Sun } from "lucide-react";

export default function Home() {
  const [feed, setFeed] = useState<string[]>([]);
  const [post, setPost] = useState("");
  const [isSimulating, setIsSimulating] = useState(false);
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const eventSource = new EventSource("http://localhost:8000/stream");
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setFeed((prev) => [data.comment, ...prev].slice(0, 50));
      } catch (e) {
        console.error("Error parsing SSE data", e);
      }
    };
    eventSource.onerror = (err) => {
      console.error("EventSource failed:", err);
      eventSource.close();
    };
    return () => eventSource.close();
  }, []);

  const handleSimulate = async () => {
    setIsSimulating(true);
    setFeed([]);
    try {
      await fetch("http://localhost:8000/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ post }),
      });
    } catch (e) {
      console.error("Simulate failed", e);
    } finally {
      setIsSimulating(false);
    }
  };

  if (!mounted) return null;

  return (
    <main className="min-h-screen bg-background text-foreground p-6 md:p-12 font-sans selection:bg-pulse/30">
      {/* Header */}
      <header className="flex justify-between items-center mb-12">
        <div>
          <h1 className="text-3xl font-black tracking-tighter text-foreground glow-text-pulse">
            AURAPULSE <span className="text-pulse">GOD VIEW</span>
          </h1>
          <p className="text-muted-foreground text-sm mt-1 font-mono tracking-tight">SYSTEM STATUS: OPTIMAL // OASIS ENGINE V1.0</p>
        </div>
        <div className="flex items-center gap-6">
           <button 
             onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
             className="p-2 rounded-lg bg-secondary hover:bg-secondary/80 transition-colors border border-border"
             aria-label="Toggle theme"
           >
             {theme === "dark" ? <Sun className="h-5 w-5 text-pulse" /> : <Moon className="h-5 w-5 text-primary" />}
           </button>
           <div className="hidden md:flex items-center gap-3">
              <div className="h-2 w-2 rounded-full bg-aquamarine animate-pulse" />
              <span className="text-xs font-mono text-muted-foreground uppercase tracking-widest">Link Active</span>
           </div>
        </div>
      </header>
      
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 h-full">
        {/* Left: Setup (4 cols) */}
        <section className="lg:col-span-4 space-y-6">
          <div className="glass-panel p-6 glow-border-pulse transition-all duration-300">
            <h2 className="text-sm font-bold uppercase tracking-widest text-muted-foreground mb-6 flex items-center gap-2">
              <span className="h-4 w-1 bg-pulse rounded-full" />
              1. Simulation Setup
            </h2>
            
            <div className="space-y-4">
              <div>
                <label className="text-[10px] font-bold uppercase text-muted-foreground mb-2 block tracking-widest">Post Narrative / Input</label>
                <textarea 
                  className="w-full h-32 bg-background/40 border border-border rounded-xl p-4 text-sm focus:outline-none focus:border-pulse/50 transition-colors placeholder:text-muted-foreground/50" 
                  placeholder="Describe the post content or paste narrative here..."
                  value={post}
                  onChange={(e) => setPost(e.target.value)}
                />
              </div>
              
              <button 
                onClick={handleSimulate}
                disabled={isSimulating || !post}
                className="w-full group relative overflow-hidden bg-pulse text-background font-black py-4 rounded-xl transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-pulse/20"
              >
                <span className="relative z-10">{isSimulating ? "INJECTING..." : "INITIALIZE SWARM"}</span>
                <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300" />
              </button>
            </div>
          </div>

          <div className="glass-panel p-6 border-dashed border-border bg-transparent">
             <h3 className="text-[10px] font-bold uppercase text-muted-foreground mb-2 tracking-widest">Persona Configuration</h3>
             <p className="text-xs text-muted-foreground/70">OASIS Swarm defaults to 1,000 parallel digital twins. Fine-tuning available in Phase 2.</p>
          </div>
        </section>
        
        {/* Center: Live Feed (5 cols) */}
        <section className="lg:col-span-5 flex flex-col h-[70vh]">
          <div className="glass-panel flex-grow flex flex-col overflow-hidden border-pulse/20 shadow-xl">
            <div className="p-4 border-b border-border flex justify-between items-center bg-muted/30">
              <h2 className="text-sm font-bold uppercase tracking-widest text-pulse flex items-center gap-2">
                <span className="h-4 w-1 bg-pulse rounded-full" />
                2. Live Swarm Feed
              </h2>
              <span className="text-[10px] font-mono text-muted-foreground">POLLING REDIS_PUB_SUB</span>
            </div>
            
            <div className="flex-grow p-6 overflow-y-auto space-y-4 custom-scrollbar bg-background/20">
               {feed.length === 0 ? (
                 <div className="h-full flex flex-col items-center justify-center text-muted-foreground/30">
                    <div className="h-12 w-12 border-2 border-muted border-t-pulse rounded-full animate-spin mb-4" />
                    <p className="text-sm italic font-mono uppercase tracking-tighter">Awaiting Signal...</p>
                 </div>
               ) : (
                 feed.map((msg, i) => (
                   <div key={i} className="group animate-in fade-in slide-in-from-left-4 duration-500">
                     <div className="flex items-start gap-3">
                        <div className="h-8 w-8 rounded-lg bg-pulse/10 border border-pulse/30 flex items-center justify-center text-[10px] font-bold text-pulse">
                          AG
                        </div>
                        <div className="flex-grow">
                          <div className="flex justify-between mb-1">
                            <span className="text-[10px] font-black uppercase text-muted-foreground tracking-wider">Agent_{feed.length - i}</span>
                            <span className="text-[8px] font-mono text-muted-foreground/50">T+{i}s</span>
                          </div>
                          <p className="text-sm text-foreground/90 leading-relaxed font-mono selection:bg-pulse/30 italic">
                            <span className="text-pulse mr-2 not-italic font-bold">&gt;</span>{msg}
                          </p>
                        </div>
                     </div>
                     <div className="mt-4 h-[1px] w-full bg-gradient-to-r from-border to-transparent" />
                   </div>
                 ))
               )}
            </div>
          </div>
        </section>

        {/* Right: Analytics (3 cols) */}
        <section className="lg:col-span-3 space-y-6">
          <div className="glass-panel p-6 border-destructive/20">
            <h2 className="text-sm font-bold uppercase tracking-widest text-destructive mb-6 flex items-center gap-2">
              <span className="h-4 w-1 bg-destructive rounded-full" />
              3. Predictive ROI
            </h2>
            
            <div className="space-y-8">
               <div className="relative h-32 w-32 mx-auto">
                  <div className="absolute inset-0 border-4 border-muted rounded-full" />
                  <div className="absolute inset-0 border-4 border-pulse rounded-full border-t-transparent animate-[spin_3s_linear_infinite]" />
                  <div className="absolute inset-0 flex items-center justify-center flex-col">
                    <span className="text-2xl font-black text-foreground">--</span>
                    <span className="text-[8px] font-bold text-muted-foreground uppercase tracking-tighter">Confidence</span>
                  </div>
               </div>

               <div className="space-y-4">
                  {[
                    { label: "Viral Potential", color: "bg-pulse" },
                    { label: "Brand Safety", color: "bg-destructive" },
                    { label: "Sentiment Shift", color: "bg-accent" }
                  ].map((item) => (
                    <div key={item.label}>
                      <div className="flex justify-between text-[10px] font-bold uppercase text-muted-foreground mb-2 tracking-widest">
                        <span>{item.label}</span>
                        <span>0%</span>
                      </div>
                      <div className="h-1 w-full bg-muted rounded-full overflow-hidden">
                        <div className={`h-full w-0 ${item.color} transition-all duration-1000`} />
                      </div>
                    </div>
                  ))}
               </div>
            </div>
          </div>

          <div className="glass-panel p-6 bg-pulse/5 border-pulse/20">
             <p className="text-[10px] leading-relaxed text-pulse font-mono italic">
               "The simulation is a reflection of current cultural vectors. Accuracy increases with GraphRAG depth."
             </p>
          </div>
        </section>
      </div>
      
      <style jsx global>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: var(--muted);
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: var(--muted-foreground);
        }
      `}</style>
    </main>
  );
}
