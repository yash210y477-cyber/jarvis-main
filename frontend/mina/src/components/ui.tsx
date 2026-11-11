import { useMemo, useRef, type ElementType, type ReactNode, type CSSProperties } from 'react';
import { motion, useScroll, useTransform, type MotionValue } from 'framer-motion';

type FadeProps = { children: ReactNode; delay?: number; duration?: number; x?: number; y?: number; as?: ElementType; className?: string; style?: CSSProperties };
export function FadeIn({ children, delay = 0, duration = 0.7, x = 0, y = 30, as = 'div', className, style }: FadeProps) {
  const Comp = useMemo(() => motion.create(as as any), [as]) as any;
  return (
    <Comp className={className} style={style}
      initial={{ opacity: 0, x, y }} whileInView={{ opacity: 1, x: 0, y: 0 }}
      viewport={{ once: true, margin: '50px', amount: 0 }}
      transition={{ duration, delay, ease: [0.25, 0.1, 0.25, 1] }}>
      {children}
    </Comp>
  );
}

export function ContactButton({ className = '', label = 'Contact Me', onClick }: { className?: string; label?: string; onClick?: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`contact-btn rounded-full text-white font-medium uppercase tracking-widest px-8 py-3 sm:px-10 sm:py-3.5 md:px-12 md:py-4 text-xs sm:text-sm md:text-base cursor-pointer border-0 ${className}`}
      style={{
        background: 'linear-gradient(123deg, #1B120A 7%, #6B3F1D 37%, #A8651F 72%, #D9963A 100%)',
        boxShadow: '0px 4px 4px rgba(168, 101, 31, 0.25), 4px 4px 12px #A8651F inset',
        outline: '2px solid white', outlineOffset: '-3px',
      }}>
      {label}
    </button>
  );
}

export function LiveProjectButton() {
  return (
    <button className="rounded-full border-2 border-[#D7E2EA] text-[#D7E2EA] font-medium uppercase tracking-widest px-8 py-3 sm:px-10 sm:py-3.5 text-sm sm:text-base hover:bg-[#D7E2EA]/10 transition-colors bg-transparent cursor-pointer">
      Live Project
    </button>
  );
}

export function Magnet({ children, padding = 100, strength = 2 }: { children: ReactNode; padding?: number; strength?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const onMove = (e: MouseEvent | React.MouseEvent) => {
    const el = ref.current; if (!el) return;
    const r = el.getBoundingClientRect();
    const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    const dx = Math.abs(cx - e.clientX), dy = Math.abs(cy - e.clientY);
    const near = dx < r.width / 2 + padding && dy < r.height / 2 + padding;
    el.style.transition = near ? 'transform 0.3s ease-out' : 'transform 0.6s ease-in-out';
    el.style.transform = near ? `translate3d(${(e.clientX - cx) / strength}px, ${(e.clientY - cy) / strength}px, 0)` : 'translate3d(0,0,0)';
  };
  return (
    <div ref={ref} onMouseMove={onMove} onMouseLeave={() => { if (ref.current) { ref.current.style.transition = 'transform 0.6s ease-in-out'; ref.current.style.transform = 'translate3d(0,0,0)'; } }} style={{ willChange: 'transform', display: 'inline-block' }}>
      {children}
    </div>
  );
}

function Char({ ch, progress, range }: { ch: string; progress: MotionValue<number>; range: [number, number] }) {
  const opacity = useTransform(progress, range, [0.2, 1]);
  return (
    <span className="relative inline-block">
      <span className="invisible">{ch}</span>
      <motion.span className="absolute left-0 top-0" style={{ opacity }}>{ch}</motion.span>
    </span>
  );
}

export function AnimatedText({ text, className, style }: { text: string; className?: string; style?: CSSProperties }) {
  const ref = useRef<HTMLParagraphElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start 0.8', 'end 0.2'] });
  const total = text.length;
  let i = 0;
  return (
    <p ref={ref} className={className} style={style}>
      {text.split(' ').map((word, w, arr) => (
        <span key={w} className="inline-block whitespace-nowrap">
          {word.split('').map((ch) => {
            const s = i / total, e = (i + 1) / total; i++;
            return <Char key={i} ch={ch} progress={scrollYProgress} range={[s, e]} />;
          })}
          {w < arr.length - 1 && (() => { i++; return <span>&nbsp;</span>; })()}
        </span>
      ))}
    </p>
  );
}
