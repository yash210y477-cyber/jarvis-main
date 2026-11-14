export const USER_NAME = 'Yash';
export const API = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8080';
export const TOKEN = import.meta.env.VITE_JARVIS_TOKEN ?? '';

export const MODELS = ['auto', 'openrouter', 'groq', 'cerebras', 'deepseek', 'zai', 'siliconflow', 'llama3 (local)'];
export const MODES = ['Assistant', 'Coder', 'Researcher', 'Friend'];
