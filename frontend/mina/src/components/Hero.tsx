import { useEffect, useState } from 'react';
import { Wifi, Cloud } from 'lucide-react';
import { FadeIn, ContactButton } from './ui';
import Portrait from './Portrait';
import { useJarvis } from '../state';
import { USER_NAME } from '../config';

const links = ['Dashboard', 'Chat', 'Memory', 'Models', 'Settings'];
const greet = () => { const h = new Date().getHours(); return h < 12 ? 'Good Morning' : h < 17 ? 'Good Afternoon' : 'Good Evening'; };
const chip = 'flex items-center gap-2 rounded-full border border-[#D7E2EA]/40 px-3 py-1 text-[#D7E2EA] uppercase tracking-widest text-[10px] sm:text-xs';

/** The clock ticks on its own, so the rest of the hero (and the portrait) never re-renders with it. */
function Clock() {
  const [time, setTime] = useState(() => new Date());
  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);
  return <div className="text-[#D7E2EA] font-medium tracking-widest text-sm sm:text-base tabular-nums">{time.toLocaleTimeString('en-GB')}</div>;
}

export default function HeroSection() {
  const { toggleMic, status, model } = useJarvis();
  const [online, setOnline] = useState(navigator.onLine);
  useEffect(() => {
    const on = () => setOnline(true), off = () => setOnline(false);
    addEventListener('online', on); addEventListener('offline', off);
    return () => { removeEventListener('online', on); removeEventListener('offline', off); };
  }, []);

  return (
    <section className="relative h-screen flex flex-col" style={{ overflowX: 'clip', background: '#0C0C0C' }}>
      <FadeIn delay={0} y={-20}>
        <nav className="flex justify-between px-6 md:px-10 pt-6 md:pt-8">
          {links.map((l) => (
            <a key={l} href={`#${l.toLowerCase()}`} className="text-[#D7E2EA] font-medium uppercase tracking-wider text-xs sm:text-sm md:text-lg lg:text-[1.4rem] hover:opacity-70 transition-opacity duration-200">{l}</a>
          ))}
        </nav>
      </FadeIn>

      <div className="overflow-hidden">
        <FadeIn delay={0.15} y={40}>
          <h1 className="hero-heading font-black uppercase tracking-tight leading-none whitespace-nowrap w-full mt-6 sm:mt-4 md:-mt-5 text-[12vw] sm:text-[13vw] md:text-[14vw] lg:text-[15vw]">
            Hi, i’m jarvis
          </h1>
        </FadeIn>
      </div>

      <FadeIn delay={0.25} y={20}>
        <div className="flex justify-between items-start gap-3 px-6 md:px-10 mt-3">
          <div className={chip + ' normal-case tracking-wide text-xs sm:text-sm'}>{greet()}, <b>{USER_NAME}</b> 👋</div>
          <div className="flex flex-col items-end gap-2">
            <div className={chip}><Wifi size={14} /> {online ? 'Online' : 'Offline'}</div>
            <div className={chip}><Cloud size={14} /> {model}</div>
            <Clock />
          </div>
        </div>
      </FadeIn>

      <div className="flex-1" />

      <div className="flex justify-between items-end px-6 md:px-10 pb-7 sm:pb-8 md:pb-10">
        <FadeIn delay={0.35} y={20}>
          <p className="text-[#D7E2EA] font-light uppercase tracking-wide leading-snug max-w-[160px] sm:max-w-[220px] md:max-w-[260px]" style={{ fontSize: 'clamp(0.75rem, 1.4vw, 1.5rem)' }}>
            jarvis — just a rather very intelligent system
          </p>
        </FadeIn>
        <FadeIn delay={0.5} y={20}>
          <ContactButton label={status === 'listening' ? 'Listening…' : 'Talk to Jarvis'} onClick={toggleMic} />
        </FadeIn>
      </div>

      <Portrait />
    </section>
  );
}
