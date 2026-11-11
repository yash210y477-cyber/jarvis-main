import { createContext, useContext, useRef, useState, type ReactNode } from 'react';
import { USER_NAME } from './config';
import { askJarvis, say, stopSpeaking } from './lib/jarvis';

export type Msg = { role: 'user' | 'jarvis'; text: string };
export type Status = 'idle' | 'listening' | 'thinking' | 'speaking';
type Ctx = {
  messages: Msg[]; status: Status; model: string; setModel: (m: string) => void; mode: string; setMode: (m: string) => void;
  voiceReplies: boolean; setVoiceReplies: (v: boolean) => void;
  send: (t: string) => Promise<void>; toggleMic: () => void; jarvisSays: (t: string) => void;
};
const C = createContext<Ctx>(null as unknown as Ctx);
export const useJarvis = () => useContext(C);

export function JarvisProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<Msg[]>([
    { role: 'jarvis', text: `Hello ${USER_NAME} 👋` },
    { role: 'jarvis', text: "I'm JARVIS. How may I assist you today?" },
  ]);
  const [status, setStatus] = useState<Status>('idle');
  const [model, setModel] = useState('gemini');
  const [mode, setMode] = useState('Assistant');
  const [voiceReplies, setVoiceReplies] = useState(true);
  const rec = useRef<any>(null);

  const speak = (text: string, voice = voiceReplies) => { setStatus('idle'); say(text, voice, (on) => setStatus(on ? 'speaking' : 'idle')); };
  const jarvisSays = (text: string) => { setMessages((m) => [...m, { role: 'jarvis', text }]); speak(text); };
  const send = async (text: string) => {
    const t = text.trim(); if (!t) return;
    setMessages((m) => [...m, { role: 'user', text: t }]); setStatus('thinking');
    const reply = await askJarvis(t, mode, model);
    setMessages((m) => [...m, { role: 'jarvis', text: reply }]); speak(reply);
  };
  const toggleMic = () => {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) return jarvisSays('Voice input is not supported in this browser. Please use Chrome.');
    if (rec.current) { rec.current.stop(); return; }
    stopSpeaking();
    const r = new SR(); r.lang = 'en-IN'; r.interimResults = false;
    r.onstart = () => setStatus('listening');
    r.onresult = (e: any) => send(e.results[0][0].transcript);
    r.onend = () => { rec.current = null; setStatus((s) => (s === 'listening' ? 'idle' : s)); };
    rec.current = r; r.start();
  };
  return <C.Provider value={{ messages, status, model, setModel, mode, setMode, voiceReplies, setVoiceReplies, send, toggleMic, jarvisSays }}>{children}</C.Provider>;
}
