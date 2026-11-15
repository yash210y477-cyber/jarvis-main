import { useEffect, useState, type ReactNode } from 'react';
import { usePolling } from '../lib/usePolling';
import { Brain, Trash2, Plus, Check } from 'lucide-react';
import { FadeIn } from './ui';
import { useJarvis } from '../state';
import { MODELS } from '../config';
import { getMemory, addMemoryNote, deleteMemoryNote, deleteMemoryFact, getVoices, getLanguage, getChats, getChat, setJarvisVoice, setLanguage, previewVoice, type ChatLine, type ChatSummary, type LanguageOption, type MemoryFact, type Voice } from '../lib/jarvis';

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
  const [chats, setChats] = useState<ChatSummary[]>([]);
  const [openChat, setOpenChat] = useState(0);
  const [lines, setLines] = useState<Record<number, ChatLine[]>>({});

  const load = async () => {
    const m = await getMemory();
    const c = await getChats();
    if (c) setChats(c);
    if (!m) { setOffline(true); return; }
    setOffline(false); setNotes(m.notes); setFacts(m.facts);
  };
  usePolling(load, 20000);

  // Old conversations: the list is cheap, the messages load when opened.
  const open = async (id: number) => {
    if (openChat === id) { setOpenChat(0); return; }
    setOpenChat(id);
    if (!lines[id]) {
      const messages = await getChat(id);
      if (messages) setLines((current) => ({ ...current, [id]: messages }));
    }
  };

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

        <div className="mt-6">
          <p className="font-medium uppercase tracking-widest text-xs opacity-50 mb-2">Past chats</p>
          {chats.length === 0 && <p className="font-light opacity-60">No earlier conversations yet.</p>}
          {chats.map((c) => (
            <div key={c.id} className="border-t border-[#D7E2EA]/15">
              <button onClick={() => open(c.id)} className="w-full flex justify-between items-center gap-3 py-3 bg-transparent border-0 text-left font-light cursor-pointer hover:opacity-70">
                <span className="break-words"><span className="opacity-60">{c.date} — </span>{c.title}</span>
                <span className="text-xs opacity-50 shrink-0">{c.messages} msgs</span>
              </button>
              {openChat === c.id && (
                <div className="flex flex-col gap-2 pb-4 text-sm font-light">
                  {(lines[c.id] ?? []).map((line, i) => (
                    <p key={i} className="whitespace-pre-wrap">
                      <span className="opacity-60 uppercase text-[10px] tracking-widest mr-2">{line.role === 'user' ? 'You' : 'Jarvis'}</span>
                      {line.text}
                    </p>
                  ))}
                  {(lines[c.id] ?? []).length === 0 && <p className="opacity-60">Loading…</p>}
                </div>
              )}
            </div>
          ))}
        </div>
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
  const { voiceReplies, setVoiceReplies } = useJarvis();
  const [voices, setVoices] = useState<Voice[]>([]);
  const [voice, setVoice] = useState('');
  const [inUse, setInUse] = useState('');
  const [note, setNote] = useState('');
  const [languages, setLanguages] = useState<LanguageOption[]>([]);
  const [mode, setMode] = useState('');
  const [langNote, setLangNote] = useState('');

  useEffect(() => {
    getVoices().then((d) => { if (d) { setVoices(d.voices); setVoice(d.current); setInUse(d.current); } });
    getLanguage().then((d) => { if (d) { setLanguages(d.options); setMode(d.mode); } });
  }, []);

  const chooseLanguage = async (id: string) => {
    const d = await setLanguage(id);
    if (d?.success) {
      setMode(id);
      setLangNote(`Replies will be in ${languages.find((l) => l.id === id)?.label ?? id}.`);
    } else {
      setLangNote(d?.error ?? 'Could not change the reply language.');
    }
  };

  const label = (id: string) => {
    const v = voices.find((item) => item.id === id);
    if (!v) return id;
    return v.gender ? `${v.name} (${v.gender}, ${v.accent})` : `${v.name} (${v.accent})`;
  };

  // Choosing is free; Confirm is what the assistant actually uses.
  const pick = (id: string) => {
    setVoice(id);
    setNote(id === inUse ? 'Already in use.' : 'Selected — press Confirm to use this voice.');
  };

  const confirm = async () => {
    const d = await setJarvisVoice(voice);

    if (d?.success) {
      setInUse(voice);
      setNote(`Voice confirmed: ${label(voice)}`);
    } else {
      setNote(d?.error ?? 'Could not switch the voice.');
    }
  };

  const preview = async () => {
    setNote('Playing…');
    const d = await previewVoice(voice);
    setNote(d?.success ? 'That was the selected voice. Press Confirm to keep it.' : d?.error ?? 'Preview failed.');
  };

  return (
    <div id="settings">
      <Head>Settings</Head>
      <div className={box + ' flex flex-col gap-4'}>
        {languages.length > 0 && (
          <label className="flex flex-col gap-2 font-medium uppercase tracking-widest text-sm sm:text-base">
            Reply language
            <div className="flex flex-wrap gap-3 items-center">
              <select value={mode} onChange={(e) => chooseLanguage(e.target.value)} className="bg-[#0C0C0C] border border-[#D7E2EA]/40 rounded-full px-4 py-2 text-sm cursor-pointer">
                {languages.map((l) => <option key={l.id} value={l.id}>{l.label}</option>)}
              </select>
            </div>
            {langNote && <span className="text-[11px] normal-case tracking-normal opacity-70">{langNote}</span>}
          </label>
        )}
        <label className="flex justify-between items-center gap-4 cursor-pointer font-medium uppercase tracking-widest text-sm sm:text-base">
          Spoken replies
          <input type="checkbox" checked={voiceReplies} onChange={(e) => setVoiceReplies(e.target.checked)} className="w-5 h-5 accent-[#A8651F]" />
        </label>
        {voices.length > 0 && (
          <label className="flex flex-col gap-2 font-medium uppercase tracking-widest text-sm sm:text-base">
            Voice
            <div className="flex flex-wrap gap-3 items-center">
              <select value={voice} onChange={(e) => pick(e.target.value)} className="bg-[#0C0C0C] border border-[#D7E2EA]/40 rounded-full px-4 py-2 text-sm cursor-pointer">
                {voices.map((v) => (
                  <option key={v.id} value={v.id}>{v.gender ? `${v.name} — ${v.gender}, ${v.accent}` : `${v.name} — ${v.accent}`}</option>
                ))}
              </select>
              <button className={ghost} onClick={preview}>Preview voice</button>
              <button className={ghost + ' !border-[#A8651F]'} onClick={confirm}>Confirm</button>
            </div>
            {inUse && <span className="text-[11px] normal-case tracking-normal opacity-60">In use: {label(inUse)}</span>}
            {note && <span className="text-[11px] normal-case tracking-normal opacity-70">{note}</span>}
          </label>
        )}
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
