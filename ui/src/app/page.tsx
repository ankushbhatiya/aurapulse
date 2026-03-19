"use client";
import { useState, useEffect } from 'react';

export default function Home() {
  const [feed, setFeed] = useState<string[]>([]);

  useEffect(() => {
    const eventSource = new EventSource("http://localhost:8000/stream");
    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setFeed((prev) => [...prev, data.comment]);
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

  return (
    <main className="min-h-screen bg-[#09090b] text-white p-8">
      <header className="mb-8 border-b border-zinc-800 pb-4">
        <h1 className="text-2xl font-bold text-[#00f6ff]">AuraPulse God View</h1>
      </header>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 h-[80vh]">
        {/* Left: Setup */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
          <h2 className="text-lg font-semibold mb-4">1. Setup Simulation</h2>
          <div className="text-zinc-500 text-sm">Form will go here</div>
        </div>
        
        {/* Center: Live Feed */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 flex flex-col">
          <h2 className="text-lg font-semibold mb-4 text-[#64ffda]">2. Live Swarm Feed</h2>
          <div className="flex-grow bg-black rounded-lg border border-zinc-800 p-4 overflow-y-auto">
             {feed.length === 0 ? (
               <div className="text-zinc-500 text-sm italic">Waiting for simulation...</div>
             ) : (
               feed.map((msg, i) => (
                 <div key={i} className="mb-2 text-sm text-zinc-300 font-mono">
                   &gt; {msg}
                 </div>
               ))
             )}
          </div>
        </div>

        {/* Right: Analytics */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
          <h2 className="text-lg font-semibold mb-4 text-[#ff0055]">3. Predictive ROI</h2>
          <div className="text-zinc-500 text-sm">Charts will go here</div>
        </div>
      </div>
    </main>
  );
}
