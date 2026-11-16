import { useEffect, useRef, useState } from 'react';
import { Bot, Download, FileCode, Mic, Send, User } from 'lucide-react';
import { FadeIn } from './ui';
import { useJarvis } from '../state';
import { MODES } from '../config';
import { fileHref, imageSrc, saveFile, saveImage } from '../lib/jarvis';

const GRAD = 'linear-gradient(123deg, #1B120A 7%, #6B3F1D 37%, #A8651F 72%, #D9963A 100%)';
const IMAGE_OR_FILE = /!\[[^\]]*\]\(([^)]+)\)|\[file\](\S+)|\[ask\]/g;

// A reply can carry pictures ("![image](/images/file.png)") and files
// ("[file]chess.py"). Both are shown in the chat, and only copied to
// Downloads/Jarvis when the download button is pressed.
function parts(text: string): { text?: string; image?: string; file?: string; ask?: boolean }[] {
  const out: { text?: string; image?: string; file?: string; ask?: boolean }[] = [];
  const re = new RegExp(IMAGE_OR_FILE.source, 'g');
  let last = 0;
  let found: RegExpExecArray | null;
  while ((found = re.exec(text))) {
    if (found.index > last) out.push({ text: text.slice(last, found.index) });
    if (found[1]) out.push({ image: found[1] });
    else if (found[2]) out.push({ file: found[2] });
    else out.push({ ask: true });
    last = found.index + found[0].length;
  }
  if (last < text.length) out.push({ text: text.slice(last) });
  return out;
}

function Picture({ url }: { url: string }) {
  const [note, setNote] = useState('');
  const name = url.split('/').pop() || '';
  const save = async () => { setNote('Saving…'); setNote(await saveImage(name)); };
  return (
    <div className="flex flex-col gap-2 my-1">
      <img src={imageSrc(url)} alt="Jarvis image" className="rounded-2xl max-h-72 max-w-full object-contain bg-black/20" />
      <button onClick={save} className="self-start flex items-center gap-2 rounded-full border-2 border-[#D7E2EA]/60 px-4 py-1.5 text-[11px] uppercase tracking-widest bg-transparent cursor-pointer hover:bg-[#D7E2EA]/10">
        <Download size={13} /> Download
      </button>
      {note && <span className="text-[11px] opacity-70 break-all">{note}</span>}
    </div>
  );
}

function FileCard({ path }: { path: string }) {
  const [note, setNote] = useState('');
  const name = decodeURIComponent(path.split('/').pop() || 'file');
  const save = async () => { setNote('Saving…'); setNote(await saveFile(path)); };
  return (
    <div className="flex flex-col gap-2 my-1">
      <div className="flex items-center gap-3 rounded-2xl border border-[#D7E2EA]/40 px-4 py-3">
        <FileCode size={22} />
        <a href={fileHref(path)} download={name} className="text-sm break-all underline decoration-dotted">{name}</a>
      </div>
      <button onClick={save} className="self-start flex items-center gap-2 rounded-full border-2 border-[#D7E2EA]/60 px-4 py-1.5 text-[11px] uppercase tracking-widest bg-transparent cursor-pointer hover:bg-[#D7E2EA]/10">
        <Download size={13} /> Download
      </button>
      {note && <span className="text-[11px] opacity-70 break-all">{note}</span>}
    </div>
  );
}

// Every reply says which provider and model really answered it.
function Who({ answered, model }: { answered: string; model?: string }) {
  return (
    <div className="mt-2 text-[10px] tracking-wide opacity-50">
      via {answered}{model ? ` · ${model}` : ''}
    </div>
  );
}

// A guarded action asks in plain words, and the answer is one click.
function AskCard({ onAnswer }: { onAnswer?: (text: string) => void }) {
  if (!onAnswer) return null;
  return (
    <div className="flex flex-wrap gap-2 my-2">
      <button onClick={() => onAnswer('yes')} className="rounded-full px-5 py-1.5 text-[11px] uppercase tracking-widest cursor-pointer text-white border-0" style={{ background: GRAD }}>Allow</button>
      <button onClick={() => onAnswer('no')} className="rounded-full border-2 border-[#D7E2EA]/60 px-5 py-1.5 text-[11px] uppercase tracking-widest bg-transparent cursor-pointer hover:bg-[#D7E2EA]/10">Cancel</button>
    </div>
  );
}

function Bubble({ text, onAnswer }: { text: string; onAnswer?: (text: string) => void }) {
  return (
    <>
      {parts(text).map((part, i) => part.image
        ? <Picture key={i} url={part.image} />
        : part.file
          ? <FileCard key={i} path={part.file} />
          : part.ask
            ? <AskCard key={i} onAnswer={onAnswer} />
            : <span key={i} className="whitespace-pre-wrap">{part.text}</span>)}
    </>
  );
}

export default function Chat() {
  const { messages, send, toggleMic, status, mode, setMode, model } = useJarvis();
  const [text, setText] = useState('');
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => { end.current?.parentElement?.scrollTo({ top: 1e6, behavior: 'smooth' }); }, [messages, status]);
  const go = () => { send(text); setText(''); };
  return (
    <section id="chat" className="rounded-t-[40px] sm:rounded-t-[50px] md:rounded-t-[60px] px-5 sm:px-8 md:px-10 py-20 sm:py-24 md:py-32" style={{ background: '#FFFFFF' }}>
      <FadeIn><h2 className="font-black uppercase text-center mb-12 sm:mb-16" style={{ color: '#0C0C0C', fontSize: 'clamp(3rem, 12vw, 160px)' }}>AI Chat</h2></FadeIn>
      <FadeIn>
        <div className="max-w-3xl mx-auto rounded-[32px] sm:rounded-[40px] overflow-hidden text-[#D7E2EA]" style={{ background: '#0C0C0C' }}>
          <div className="flex items-center justify-between gap-3 p-5 border-b border-[#D7E2EA]/20">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-2xl flex items-center justify-center text-white" style={{ background: GRAD }}><Bot size={24} /></div>
              <div><div className="font-bold uppercase tracking-widest text-xl">Jarvis</div><div className="text-xs uppercase tracking-widest opacity-60">{status === 'idle' ? 'AI Assistant Online' : status}</div></div>
            </div>
            <select value={mode} onChange={(e) => setMode(e.target.value)} className="bg-transparent border border-[#D7E2EA]/40 rounded-full px-4 py-2 text-sm cursor-pointer">
              {MODES.map((m) => <option key={m} className="bg-[#0C0C0C]">{m}</option>)}
            </select>
          </div>
          <div className="h-[380px] overflow-y-auto p-5 flex flex-col gap-3">
            {messages.map((m, i) => (
              <div key={i} className={`flex items-end gap-2 ${m.role === 'user' ? 'flex-row-reverse' : ''}`}>
                <div className="w-8 h-8 rounded-full border border-[#D7E2EA]/40 flex items-center justify-center shrink-0">{m.role === 'user' ? <User size={14} /> : <Bot size={14} />}</div>
                <div className={`rounded-3xl px-5 py-3 max-w-[80%] font-light leading-relaxed ${m.role === 'user' ? 'text-white' : 'bg-[#D7E2EA]/10'}`} style={m.role === 'user' ? { background: GRAD } : undefined}>
                  <Bubble text={m.text} onAnswer={m.role === 'user' ? undefined : send} />
                  {m.role === 'jarvis' && m.provider && <Who answered={m.provider} model={m.model} />}
                </div>
              </div>
            ))}
            {status === 'thinking' && <div className="opacity-60 text-sm animate-pulse pl-10">Jarvis is thinking…</div>}
            <div ref={end} />
          </div>
          <div className="flex items-center gap-3 p-4 border-t border-[#D7E2EA]/20">
            <input value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && go()} placeholder="Ask Jarvis anything..." className="flex-1 min-w-0 bg-[#D7E2EA]/10 rounded-full px-5 py-3 outline-none placeholder:text-[#D7E2EA]/50" />
            <button onClick={toggleMic} aria-label="Microphone" className={`w-12 h-12 rounded-full border-2 border-[#D7E2EA] flex items-center justify-center cursor-pointer bg-transparent text-[#D7E2EA] hover:bg-[#D7E2EA]/10 ${status === 'listening' ? 'animate-pulse' : ''}`}><Mic size={18} /></button>
            <button onClick={go} aria-label="Send" className="w-12 h-12 rounded-full flex items-center justify-center text-white cursor-pointer border-0" style={{ background: GRAD }}><Send size={18} /></button>
          </div>
        </div>
      </FadeIn>
    </section>
  );
}
