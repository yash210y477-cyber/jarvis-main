import { useEffect, useRef, useState } from 'react';
import { Bot, Mic, Send, User } from 'lucide-react';
import { FadeIn } from './ui';
import { useJarvis } from '../state';
import { MODES } from '../config';

const GRAD = 'linear-gradient(123deg, #1B120A 7%, #6B3F1D 37%, #A8651F 72%, #D9963A 100%)';

export default function Chat() {
  const { messages, send, toggleMic, status, mode, setMode } = useJarvis();
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
                <div className={`rounded-3xl px-5 py-3 max-w-[80%] font-light leading-relaxed ${m.role === 'user' ? 'text-white' : 'bg-[#D7E2EA]/10'}`} style={m.role === 'user' ? { background: GRAD } : undefined}>{m.text}</div>
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
