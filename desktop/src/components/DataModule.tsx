import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

/**
 * Component for displaying execution metrics and status distribution.
 * 
 * This component simulates or fetches metrics and renders them in a styled container.
 * 
 * @returns {React.ReactElement} The rendered data module component.
 */
const DataModule: React.FC = () => {
  const [stats, setStats] = useState<{ success: number; failure: number; total: number } | null>(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await fetch('http://localhost:8000/analytics').catch(() => null);
        if (res && res.ok) {
          const data = await res.json();
          setStats(data);
        }
      } catch (e) {
        console.error("Failed to fetch analytics", e);
      }
    };

    fetchStats();
    const interval = setInterval(fetchStats, 3000);
    return () => clearInterval(interval);
  }, []);

  if (!stats || stats.total === 0) {
    return (
      <div className="p-6 bg-surface rounded-2xl border border-glass mt-auto opacity-50">
        <h3 className="text-[10px] font-black text-muted uppercase tracking-[0.2em] mb-2">Execution Analytics</h3>
        <p className="text-[10px] italic text-muted">No execution data recorded for this session.</p>
      </div>
    );
  }

  const successRate = ((stats.success / stats.total) * 100).toFixed(0);

  return (
    <div className="p-6 bg-surface rounded-2xl border border-glass mt-auto transition-all">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-[10px] font-black text-muted uppercase tracking-[0.2em]">Execution Analytics</h3>
        <span className="text-[10px] font-bold text-primary bg-primary/10 px-2 py-0.5 rounded-full">{successRate}% Success</span>
      </div>
      
      <div className="grid grid-cols-3 gap-2 mb-4">
        <div className="bg-black/30 p-2 rounded-lg border border-white/5 text-center">
          <div className="text-[10px] text-muted uppercase font-black tracking-tighter mb-1">Pass</div>
          <div className="text-sm font-bold text-success">{stats.success}</div>
        </div>
        <div className="bg-black/30 p-2 rounded-lg border border-white/5 text-center">
          <div className="text-[10px] text-muted uppercase font-black tracking-tighter mb-1">Fail</div>
          <div className="text-sm font-bold text-error">{stats.failure}</div>
        </div>
        <div className="bg-black/30 p-2 rounded-lg border border-white/5 text-center">
          <div className="text-[10px] text-muted uppercase font-black tracking-tighter mb-1">Total</div>
          <div className="text-sm font-bold text-white">{stats.total}</div>
        </div>
      </div>

      <div className="h-1 w-full bg-white/5 rounded-full overflow-hidden">
        <motion.div 
          initial={{ width: 0 }}
          animate={{ width: `${successRate}%` }}
          className="h-full bg-success"
        />
      </div>
    </div>
  );
};

export default DataModule;
