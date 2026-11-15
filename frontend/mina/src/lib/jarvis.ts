import { API, TOKEN } from '../config';

export type Stats = { cpu: number; memory: number; storage: number };

// The local API only accepts state-changing calls that carry this token.
const auth = (): Record<string, string> => (TOKEN ? { 'X-Jarvis-Token': TOKEN } : {});

const post = async (path: string, body: unknown) => {
  const r = await fetch(`${API}${path}`, { method: 'POST', headers: { 'Content-Type': 'application/json', ...auth() }, body: JSON.stringify(body) });
  if (r.status === 401) return { error: 'Local token rejected. Set VITE_JARVIS_TOKEN in frontend/mina/.env to match JARVIS_LOCAL_TOKEN, then restart the UI.' };
  return r.json();
};

export async function askJarvis(message: string, mode: string, model: string): Promise<string> {
  try { const d = await post('/chat', { message, mode, model }); return d.reply ?? d.response ?? d.error ?? 'Done.'; }
  catch { return `I can't reach my backend at ${API}. Start it and try again.`; }
}

// ---- generated pictures: shown in the chat, saved only when asked ----
export const imageSrc = (url: string) => (/^https?:/i.test(url) ? url : `${API}${url}`);

export async function saveImage(name: string): Promise<string> {
  try {
    const r = await fetch(`${API}/images/${encodeURIComponent(name)}/download`, { method: 'POST', headers: auth() });
    const d = await r.json();
    return d.success ? `Saved to ${d.path}` : (d.error ?? 'Could not save the image.');
  } catch { return 'Could not reach the backend to save the image.'; }
}

/** Message text without the image markup, for speaking aloud. */
export const plainText = (text: string) => text.replace(/!\[[^\]]*\]\([^)]*\)/g, '').replace(/\n{3,}/g, '\n\n').trim();

// ---- the six voices offered in Settings ----
export type Voice = { id: string; name: string; gender: string; accent: string };

export async function getVoices(): Promise<{ voices: Voice[]; current: string } | null> {
  try { const r = await fetch(`${API}/voice/options`); const d = await r.json(); return d.success ? { voices: d.voices ?? [], current: d.current ?? '' } : null; }
  catch { return null; }
}

export async function setJarvisVoice(voice: string) {
  try { return await post('/voice/voice', { voice }); } catch { return { success: false, error: 'Backend is not running.' }; }
}

export async function previewVoice(voice: string) {
  try { return await post('/voice/preview', { voice }); } catch { return { success: false, error: 'Backend is not running.' }; }
}
export async function launchApp(app: string): Promise<string> {
  try { const d = await post('/launch', { app }); return d.reply ?? d.error ?? `Opening ${app}.`; }
  catch { return `Couldn't open ${app}: backend at ${API} isn't responding.`; }
}
export async function getStats(): Promise<Stats | null> {
  try { const r = await fetch(`${API}/stats`); return await r.json(); } catch { return null; }
}

// ---- speaking: drives Mina's mouth through the engine hook ----
const faceSpeak = (on: boolean) => (window as any).__faceSpeak?.(on);
let token = 0, timer = 0;
export function stopSpeaking() {
  token++;
  window.clearTimeout(timer);
  if ('speechSynthesis' in window) speechSynthesis.cancel();
  stopBackendVoice();
  faceSpeak(false);
}
export function say(text: string, voice: boolean, cb: (on: boolean) => void = () => {}) {
  const t = ++token; window.clearTimeout(timer);
  const set = (on: boolean) => { if (t !== token) return; faceSpeak(on); cb(on); };
  if ('speechSynthesis' in window) speechSynthesis.cancel();
  const line = text.replace(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/gu, '').trim();
  if (!voice || !line) { set(true); timer = window.setTimeout(() => set(false), Math.min(8000, 800 + text.length * 50)); return; }
  // The confirmed voice lives in the backend engine; the browser voice is only
  // a fallback for when the backend is not running.
  set(true);
  sayOnBackend(line).then((ok) => {
    if (t !== token) return;
    if (ok) { set(false); return; }
    if ('speechSynthesis' in window) {
      const u = new SpeechSynthesisUtterance(line);
      u.onend = () => set(false); u.onerror = () => set(false);
      speechSynthesis.speak(u);
    } else set(false);
  });
}

async function sayOnBackend(text: string): Promise<boolean> {
  try { const r = await fetch(`${API}/voice/say`, { method: 'POST', headers: { 'Content-Type': 'application/json', ...auth() }, body: JSON.stringify({ text }) }); return r.ok; }
  catch { return false; }
}

function stopBackendVoice() {
  fetch(`${API}/voice/stop`, { method: 'POST', headers: auth() }).catch(() => {});
}

// ---- memory: stored on the backend, shared with chat ----
export type MemoryFact = { key: string; value: string };
export type MemoryData = { notes: string[]; facts: MemoryFact[]; profile: Record<string, string> };

export async function getMemory(): Promise<MemoryData | null> {
  try {
    const r = await fetch(`${API}/memory`);
    const d = await r.json();
    return { notes: d.notes ?? [], facts: d.facts ?? [], profile: d.profile ?? {} };
  } catch { return null; }
}

export async function addMemoryNote(text: string): Promise<string[] | null> {
  try {
    const r = await fetch(`${API}/memory`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text }) });
    const d = await r.json();
    return d.notes ?? null;
  } catch { return null; }
}

export async function deleteMemoryNote(index: number): Promise<string[] | null> {
  try {
    const r = await fetch(`${API}/memory/note/${index}`, { method: 'DELETE', headers: auth() });
    const d = await r.json();
    return d.notes ?? null;
  } catch { return null; }
}

export async function deleteMemoryFact(key: string): Promise<MemoryFact[] | null> {
  try {
    const r = await fetch(`${API}/memory/fact/${encodeURIComponent(key)}`, { method: 'DELETE', headers: auth() });
    const d = await r.json();
    return d.facts ?? null;
  } catch { return null; }
}
