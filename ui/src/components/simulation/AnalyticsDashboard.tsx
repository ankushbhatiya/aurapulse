"use client";
import { BarChart3, FileText, RotateCcw, AlertTriangle } from "lucide-react";
import { SimulationMessage } from "./SimulationFeed";

export interface SimulationReport {
  confidence_score: number;
  viral_momentum: number;
  controversy_risk: number;
  community_drift: number;
  top_risk_factor: string;
  sentiment_summary: string;
}

interface AnalyticsDashboardProps {
  reportA: SimulationReport | null;
  reportB: SimulationReport | null;
  feedA: SimulationMessage[];
  feedB: SimulationMessage[];
  isGeneratingReport: boolean;
  fetchReports: (force: boolean) => void;
}

export function AnalyticsDashboard({
  reportA, reportB, feedA, feedB, isGeneratingReport, fetchReports
}: AnalyticsDashboardProps) {
  return (
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
  );
}
