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
  const wantMic = useRef(false); // the mic stays on until the button is pressed again
  const busy = useRef(false); // JARVIS is thinking or speaking
  const restart = useRef(0);

  const engine = () => {
    const w = window as any;
    return w.SpeechRecognition || w.webkitSpeechRecognition;
  };

  function stopRecognition() {
    const current = rec.current;
    rec.current = null;
    try { current?.stop(); } catch { /* already closed */ }
  }

  function scheduleRestart() {
    window.clearTimeout(restart.current);
    restart.current = window.setTimeout(() => {
      if (wantMic.current && !busy.current && !rec.current) startListening();
    }, 400);
  }

  function startListening() {
    const SR = engine();
    if (!SR) {
      wantMic.current = false;
      jarvisSays('Voice input is not supported in this browser. Please use Chrome.');
      return;
    }
    if (rec.current) return;
    stopSpeaking();
    const r = new SR();
    r.lang = 'en-IN';
    r.continuous = true;
    r.interimResults = true;
    r.onstart = () => setStatus('listening');
    r.onresult = (e: any) => {
      let final = '';
      for (let i = e.resultIndex; i < e.results.length; i += 1) {
        if (e.results[i].isFinal) final += e.results[i][0].transcript;
      }
      if (!final.trim()) return;
      // Stop listening the moment a request is clear, so JARVIS never hears itself.
      busy.current = true;
      stopRecognition();
      void send(final);
    };
    r.onerror = (e: any) => {
      if (e?.error === 'not-allowed' || e?.error === 'service-not-allowed') {
        wantMic.current = false;
        jarvisSays('Microphone permission is blocked. Allow it in Chrome, then press the mic again.');
      }
    };
    r.onend = () => {
      rec.current = null;
      setStatus((s) => (s === 'listening' ? 'idle' : s));
      // Chrome ends the session on its own after a pause; start over.
      if (wantMic.current && !busy.current) scheduleRestart();
    };
    rec.current = r;
    try { r.start(); } catch { rec.current = null; }
  }

  const speak = (text: string, voice = voiceReplies) => {
    setStatus('idle');
    say(text, voice, (on) => {
      setStatus(on ? 'speaking' : 'idle');
      if (on) return;
      busy.current = false;
      if (wantMic.current) scheduleRestart();
    });
  };

  const jarvisSays = (text: string) => { setMessages((m) => [...m, { role: 'jarvis', text }]); speak(text); };

  const send = async (text: string) => {
    const t = text.trim(); if (!t) return;
    busy.current = true;
    setMessages((m) => [...m, { role: 'user', text: t }]); setStatus('thinking');
    const reply = await askJarvis(t, mode, model);
    setMessages((m) => [...m, { role: 'jarvis', text: reply }]);
    speak(reply);
  };

  const toggleMic = () => {
    if (wantMic.current) {
      // Manual off: nothing reopens the mic until it is pressed again.
      wantMic.current = false;
      busy.current = false;
      window.clearTimeout(restart.current);
      stopRecognition();
      stopSpeaking();
      setStatus('idle');
      return;
    }
    if (!engine()) return jarvisSays('Voice input is not supported in this browser. Please use Chrome.');
    wantMic.current = true;
    startListening();
  };

  return <C.Provider value={{ messages, status, model, setModel, mode, setMode, voiceReplies, setVoiceReplies, send, toggleMic, jarvisSays }}>{children}</C.Provider>;
}
