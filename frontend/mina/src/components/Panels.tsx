import { useEffect, useState, type ReactNode } from 'react';
import { usePolling } from '../lib/usePolling';
import { Brain, Trash2, Plus, Check } from 'lucide-react';
import { FadeIn } from './ui';
import { useJarvis } from '../state';
import { MODELS } from '../config';
import { getMemory, addMemoryNote, deleteMemoryNote, deleteMemoryFact, getVoices, setJarvisVoice, previewVoice, type MemoryFact, type Voice } from '../lib/jarvis';

const Head = ({ children }: { children: ReactNode }) => (
  <FadeIn><h2 className="hero-heading font-black uppercase leading-none tracking-tight text-center mb-10 sm:mb-14" style={{ fontSize: 'clamp(3rem, 12vw, 160px)' }}>{children}</h2></FadeIn>
);
const box = 'max-w-3xl mx-auto rounded-[32px] sm:rounded-[40px] border-2 border-[#D7E2EA]/40 p-5 sm:p-6 text-[#D7E2EA]';
const ghost = 'rounded-full border-2 border-[#D7E2EA] text-[#D7E2EA] font-medium uppercase tracking-widest px-6 py-2 text-sm hover:bg-[#D7E2EA]/10 transition-colors bg-transparent cursor-pointer';

function Memory() {
  const [notes, setNotes] = useState<string[]>([]);
  const [facts, setFacts] = useState<MemoryFact[]>([]);
  const [offline, setOffline] = useState(false);
  const [t, setT] = useState('');

  const load = async () => {
    const m = await getMemory();
    if (!m) { setOffline(true); return; }
    setOffline(false); setNotes(m.notes); setFacts(m.facts);
  };
  usePolling(load, 20000);

  const add = async () => {
    const text = t.trim(); if (!text) return;
    setT('');
    const next = await addMemoryNote(text);
    if (next) { setNotes(next); setOffline(false); } else setOffline(true);
  };
  const forgetNote = async (i: number) => { const next = await deleteMemoryNote(i); if (next) setNotes(next); else load(); };
  const forgetFact = async (key: string) => { const next = await deleteMemoryFact(key); if (next) setFacts(next); else load(); };

  return (
    <div id="memory" className="mb-24 sm:mb-32">
      <Head>Memory</Head>
      <div className={box}>
        <div className="flex gap-3 mb-4">
          <input value={t} onChange={(e) => setT(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') add(); }} placeholder="Tell Jarvis something to remember..." className="flex-1 min-w-0 bg-[#D7E2EA]/10 rounded-full px-5 py-3 outline-none placeholder:text-[#D7E2EA]/50" />
          <button className={ghost} onClick={add} aria-label="Remember"><Plus size={16} /></button>
        </div>

        {offline && <p className="font-light opacity-70 mb-3">Backend not reachable — memory needs it running.</p>}

        {facts.length > 0 && (
          <p className="font-medium uppercase tracking-widest text-xs opacity-50 mb-2">Learned in chat</p>
        )}
        {facts.map((f) => (
          <div key={f.key} className="flex justify-between items-center gap-3 py-3 border-t border-[#D7E2EA]/15 font-light">
            <span><span className="opacity-60">{f.key.replace(/_/g, ' ')}:</span> {f.value}</span>
            <button aria-label={`Forget ${f.key}`} onClick={() => forgetFact(f.key)} className="bg-transparent border-0 text-[#D7E2EA] cursor-pointer hover:opacity-70"><Trash2 size={16} /></button>
          </div>
        ))}

        {notes.length === 0 && facts.length === 0 && <p className="font-light opacity-60 flex items-center gap-2"><Brain size={16} /> Nothing remembered yet.</p>}
        {notes.map((n, i) => (
          <div key={i} className="flex justify-between items-center gap-3 py-3 border-t border-[#D7E2EA]/15 font-light">
            <span>{n}</span><button aria-label="Forget" onClick={() => forgetNote(i)} className="bg-transparent border-0 text-[#D7E2EA] cursor-pointer hover:opacity-70"><Trash2 size={16} /></button>
          </div>
        ))}
      </div>
    </div>
  );
}

function Models() {
  const { model, setModel } = useJarvis();
  return (
    <div id="models" className="mb-24 sm:mb-32">
      <Head>Models</Head>
      <div className={box + ' flex flex-wrap gap-3 justify-center'}>
        {MODELS.map((m) => (
          <button key={m} onClick={() => setModel(m)} className={ghost + (model === m ? ' bg-[#D7E2EA]/20' : '')}>{model === m && <Check size={14} className="inline mr-2" />}{m}</button>
        ))}
      </div>
    </div>
  );
}

function SettingsPanel() {
  const { voiceReplies, setVoiceReplies, jarvisSays } = useJarvis();
  const [voices, setVoices] = useState<Voice[]>([]);
  const [voice, setVoice] = useState('');
  const [note, setNote] = useState('');

  useEffect(() => {
    getVoices().then((d) => { if (d) { setVoices(d.voices); setVoice(d.current); } });
  }, []);

  const pick = async (id: string) => {
    setVoice(id);
    const d = await setJarvisVoice(id);
    setNote(d?.success ? 'Voice switched — next sentence uses it.' : d?.error ?? 'Could not switch the voice.');
  };

  const preview = async () => {
    setNote('Playing…');
    const d = await previewVoice(voice);
    setNote(d?.success ? 'That was the selected voice.' : d?.error ?? 'Preview failed.');
  };

  return (
    <div id="settings">
      <Head>Settings</Head>
      <div className={box + ' flex flex-col gap-4'}>
        <label className="flex justify-between items-center gap-4 cursor-pointer font-medium uppercase tracking-widest text-sm sm:text-base">
          Spoken replies
          <input type="checkbox" checked={voiceReplies} onChange={(e) => setVoiceReplies(e.target.checked)} className="w-5 h-5 accent-[#A8651F]" />
        </label>
        {voices.length > 0 && (
          <label className="flex flex-col gap-2 font-medium uppercase tracking-widest text-sm sm:text-base">
            Voice
            <div className="flex flex-wrap gap-3 items-center">
              <select value={voice} onChange={(e) => pick(e.target.value)} className="bg-[#0C0C0C] border border-[#D7E2EA]/40 rounded-full px-4 py-2 text-sm cursor-pointer">
                {voices.map((v) => <option key={v.id} value={v.id}>{v.name} — {v.gender === 'male' ? 'male' : 'female'}, {v.accent}</option>)}
              </select>
              <button className={ghost} onClick={preview}>Preview voice</button>
            </div>
            {note && <span className="text-[11px] normal-case tracking-normal opacity-70">{note}</span>}
          </label>
        )}
        <button className={ghost + ' self-start'} onClick={() => jarvisSays("Hi, I'm Jarvis. This is how I sound when I speak.")}>Test voice</button>
      </div>
    </div>
  );
}

export default function Panels() {
  return (
    <section className="relative z-10 -mt-10 sm:-mt-12 md:-mt-14 rounded-t-[40px] sm:rounded-t-[50px] md:rounded-t-[60px] px-5 sm:px-8 md:px-10 pt-20 sm:pt-24 md:pt-32 pb-24" style={{ background: '#0C0C0C' }}>
      <Memory /><Models /><SettingsPanel />
    </section>
  );
}
