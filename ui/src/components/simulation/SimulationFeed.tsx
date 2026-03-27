"use client";
import { useMemo, memo } from 'react';
import { minidenticon } from 'minidenticons';

export interface SimulationMessage {
  persona_name: string;
  comment: string;
  bias: string;
  track_id: string;
  reply_to?: string;
}

interface SimulationFeedProps {
  feedA: SimulationMessage[];
  feedB: SimulationMessage[];
  totalExpected: number;
  isSimulating: boolean;
}

const MessageItem = memo(({ msg, isTrackA }: { msg: SimulationMessage; isTrackA: boolean }) => {
  const avatarSvg = useMemo(() => 
    `data:image/svg+xml;utf8,${encodeURIComponent(minidenticon(msg.persona_name))}`,
    [msg.persona_name]
  );

  return (
    <div className={`animate-in fade-in duration-300 ${isTrackA ? 'slide-in-from-left-2' : 'slide-in-from-right-2'}`}>
      <div className="flex items-center gap-2 mb-1">
         <img 
           src={avatarSvg} 
           alt={msg.persona_name} 
           className="h-5 w-5 rounded-md bg-white/5 p-0.5 border border-white/10" 
         />
         <span className={`text-[9px] font-black uppercase tracking-tight ${msg.bias === 'Hater' ? 'text-neon-red' : 'text-pulse'}`}>{msg.persona_name}</span>
         {msg.reply_to && <span className="text-[8px] opacity-20">→ {msg.reply_to}</span>}
      </div>
      <p className={`text-xs text-foreground/80 leading-snug font-mono italic pl-2 border-l ${isTrackA ? 'border-pulse/20' : 'border-purple-track/20'}`}>{msg.comment}</p>
    </div>
  );
});

MessageItem.displayName = "MessageItem";

export function SimulationFeed({ feedA, feedB, totalExpected, isSimulating }: SimulationFeedProps) {
  return (
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
                  <MessageItem key={`${msg.persona_name}-${i}`} msg={msg} isTrackA={true} />
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
                  <MessageItem key={`${msg.persona_name}-${i}`} msg={msg} isTrackA={false} />
                ))}
             </div>
           </div>
        </div>
      </div>
    </section>
  );
}
