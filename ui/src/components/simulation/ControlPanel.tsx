"use client";
import { Zap, Users, Play, Square } from "lucide-react";

interface ControlPanelProps {
  postA: string;
  setPostA: (v: string) => void;
  postB: string;
  setPostB: (v: string) => void;
  agentCount: number;
  setAgentCount: (v: number) => void;
  isSimulating: boolean;
  handleSimulate: () => void;
  stopSimulation: () => void;
  simulationStatusMsg: string | null;
  isGeneratingReport: boolean;
}

export function ControlPanel({
  postA, setPostA,
  postB, setPostB,
  agentCount, setAgentCount,
  isSimulating,
  handleSimulate,
  stopSimulation,
  simulationStatusMsg,
  isGeneratingReport,
}: ControlPanelProps) {
  return (
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
                onClick={() => stopSimulation()}
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
  );
}
