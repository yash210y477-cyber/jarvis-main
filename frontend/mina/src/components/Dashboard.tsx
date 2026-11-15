import { useState } from 'react';
import { usePolling } from '../lib/usePolling';
import type { LucideIcon } from 'lucide-react';
import { Globe, Code2, FolderOpen, Terminal, Calculator, Settings, Cpu, MemoryStick, HardDrive, Wifi, Mic } from 'lucide-react';
import { FadeIn } from './ui';
import { useJarvis } from '../state';
import { getStats, launchApp, type Stats } from '../lib/jarvis';

const GRAD = 'linear-gradient(123deg, #1B120A 7%, #6B3F1D 37%, #A8651F 72%, #D9963A 100%)';
const card = 'rounded-[32px] sm:rounded-[40px] border-2 border-[#D7E2EA]/40 p-5 sm:p-6';
const Tile = ({ I }: { I: LucideIcon }) => (
  <div className="w-12 h-12 rounded-2xl flex items-center justify-center text-white shrink-0" style={{ background: GRAD }}><I size={24} /></div>
);

const apps: [string, string, LucideIcon, string][] = [
  ['Chrome', 'Browse Internet', Globe, 'chrome'], ['VS Code', 'Write Code', Code2, 'vscode'], ['Explorer', 'Manage Files', FolderOpen, 'explorer'],
  ['Terminal', 'Run Commands', Terminal, 'terminal'], ['Calculator', 'Quick Math', Calculator, 'calculator'], ['Settings', 'Windows Settings', Settings, 'settings'],
];

export default function Dashboard() {
  const { status, toggleMic, jarvisSays } = useJarvis();
  const [stats, setStats] = useState<Stats>({ cpu: 41, memory: 87, storage: 34 });
  const [demo, setDemo] = useState(false);
  const [online, setOnline] = useState(navigator.onLine);
  usePolling(async () => {
    const s = await getStats();
    if (s) { setStats(s); setDemo(false); }
    else { setDemo(true); setStats((p) => ({ cpu: clamp(p.cpu + (Math.random() - .5) * 6), memory: clamp(p.memory + (Math.random() - .5) * 2), storage: p.storage })); }
    setOnline(navigator.onLine);
  }, 15000);
  const clamp = (n: number) => Math.max(5, Math.min(99, Math.round(n)));
  const rows: [string, string, number, LucideIcon][] = [
    ['CPU Usage', `${stats.cpu}%`, stats.cpu, Cpu], ['Memory', `${stats.memory}%`, stats.memory, MemoryStick],
    ['Storage', `${stats.storage}%`, stats.storage, HardDrive], ['Network', online ? 'Online' : 'Offline', online ? 100 : 0, Wifi],
  ];
  const label = { idle: 'Voice idle', listening: 'Listening…', thinking: 'Thinking…', speaking: 'Speaking…' }[status];

  return (
    <section id="dashboard" className="px-5 sm:px-8 md:px-10 py-20 sm:py-24 md:py-32" style={{ background: '#0C0C0C' }}>
      <FadeIn><h2 className="hero-heading font-black uppercase leading-none tracking-tight text-center mb-12 sm:mb-16" style={{ fontSize: 'clamp(3rem, 12vw, 160px)' }}>Dashboard</h2></FadeIn>
      <div className="max-w-6xl mx-auto flex flex-col gap-5">
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-5">
          {apps.map(([name, sub, I, key], i) => (
            <FadeIn key={key} delay={i * 0.06}>
              <button onClick={async () => jarvisSays(await launchApp(key))} className={`${card} w-full text-left bg-transparent cursor-pointer hover:bg-[#D7E2EA]/10 transition-colors flex flex-col gap-4`}>
                <Tile I={I} />
                <div><div className="text-[#D7E2EA] font-semibold uppercase" style={{ fontSize: 'clamp(1rem, 2vw, 1.6rem)' }}>{name}</div>
                  <div className="text-[#D7E2EA] font-light opacity-60" style={{ fontSize: 'clamp(0.8rem, 1.3vw, 1.05rem)' }}>{sub}</div></div>
              </button>
            </FadeIn>
          ))}
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-5">
          {rows.map(([name, val, pct, I], i) => (
            <FadeIn key={name} delay={i * 0.06}>
              <div className={`${card} flex flex-col gap-4`}>
                <div className="flex items-center gap-3"><Tile I={I} />
                  <div><div className="text-[#D7E2EA] font-light opacity-60 text-sm">{name}</div><div className="text-[#D7E2EA] font-bold" style={{ fontSize: 'clamp(1.4rem, 2.6vw, 2.2rem)' }}>{val}</div></div></div>
                <div className="h-2 rounded-full bg-[#D7E2EA]/10"><div className="h-full rounded-full transition-all duration-700" style={{ width: `${pct}%`, background: GRAD }} /></div>
              </div>
            </FadeIn>
          ))}
        </div>
        {demo && <p className="text-[#D7E2EA]/50 text-xs text-center uppercase tracking-widest">demo values — backend /stats not connected</p>}
        <FadeIn>
          <div className={`${card} flex items-center justify-between gap-4`}>
            <div className="flex items-center gap-4">
              <div className={`w-14 h-14 rounded-full border-2 border-[#D7E2EA] flex items-center justify-center text-[#D7E2EA] ${status !== 'idle' ? 'animate-pulse' : ''}`}><Mic size={24} /></div>
              <span className="text-[#D7E2EA] font-medium uppercase tracking-widest" style={{ fontSize: 'clamp(0.9rem, 1.6vw, 1.3rem)' }}>{label}</span>
            </div>
            <button onClick={toggleMic} className="w-12 h-12 rounded-full text-white flex items-center justify-center cursor-pointer border-0" style={{ background: GRAD }} aria-label="Toggle microphone"><Mic size={20} /></button>
          </div>
        </FadeIn>
      </div>
    </section>
  );
}
