import { useRef } from 'react';
import { motion, useScroll, useTransform, type MotionValue } from 'framer-motion';
import { FadeIn, LiveProjectButton } from './ui';

const img = (id: string) => `https://images.higgs.ai/?default=1&output=webp&url=https%3A%2F%2Fd8j0ntlcm91z4.cloudfront.net%2Fuser_38xzZboKViGWJOttwIXH07lWA1P%2Fhf_${id}.png&w=1280&q=85`;

const projects = [
  { name: 'Nextlevel Studio', category: 'Client', a: img('20260412_055344_5eff02e0-87a5-41ce-b64f-eb08da8f33db'), b: img('20260412_055431_11d841fd-8b41-46a5-82e4-b04f2407a7d8'), c: img('20260412_055451_e317bf2d-28d4-48cc-86b0-6f72f25b6327') },
  { name: 'Aura Brand Identity', category: 'Personal', a: img('20260412_055654_911201c5-36d9-4bc6-bac7-331adfce159f'), b: img('20260412_055723_5ceda0b8-d9c2-4665-b2e3-83ba19ba76d1'), c: img('20260412_055753_adc5dcbd-a8e6-49c0-b43a-9b030d835cea') },
  { name: 'Solaris Digital', category: 'Client', a: img('20260412_055759_963cfb0b-4bd1-4b0f-9d0a-09bd6cf95b2f'), b: img('20260412_060108_438f781a-9846-4dcc-89ab-c4e6cb830f5b'), c: img('20260412_055818_9d062121-ad7e-46b9-999a-1a6a692ef1ee') },
];

const R = 'rounded-[40px] sm:rounded-[50px] md:rounded-[60px]';

function Card({ i, p, progress, total }: { i: number; p: (typeof projects)[number]; progress: MotionValue<number>; total: number }) {
  const target = 1 - (total - 1 - i) * 0.03;
  const scale = useTransform(progress, [i / total, 1], [1, target]);
  return (
    <div className="h-[85vh]">
      <motion.div
        className={`sticky top-24 md:top-32 border-2 border-[#D7E2EA] p-4 sm:p-6 md:p-8 ${R}`}
        style={{ scale, top: undefined, background: '#0C0C0C', marginTop: i * 28, transformOrigin: 'top center' }}>
        <div className="flex items-center justify-between gap-4 flex-wrap mb-4 sm:mb-6">
          <div className="flex items-center gap-4 sm:gap-8">
            <span className="hero-heading font-black leading-none" style={{ fontSize: 'clamp(3rem, 10vw, 140px)' }}>{String(i + 1).padStart(2, '0')}</span>
            <div className="flex flex-col text-[#D7E2EA] uppercase">
              <span className="font-light tracking-wide opacity-60" style={{ fontSize: 'clamp(0.75rem, 1.2vw, 1.1rem)' }}>{p.category}</span>
              <span className="font-medium" style={{ fontSize: 'clamp(1rem, 2.2vw, 2.1rem)' }}>{p.name}</span>
            </div>
          </div>
          <LiveProjectButton />
        </div>
        <div className="flex gap-3 sm:gap-4">
          <div className="flex flex-col gap-3 sm:gap-4" style={{ width: '40%' }}>
            <img src={p.a} alt="" loading="lazy" className={`w-full object-cover ${R}`} style={{ height: 'clamp(130px, 16vw, 230px)' }} />
            <img src={p.b} alt="" loading="lazy" className={`w-full object-cover ${R}`} style={{ height: 'clamp(160px, 22vw, 340px)' }} />
          </div>
          <div style={{ width: '60%' }}>
            <img src={p.c} alt="" loading="lazy" className={`w-full h-full object-cover ${R}`} />
          </div>
        </div>
      </motion.div>
    </div>
  );
}

export default function ProjectsSection() {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start start', 'end end'] });
  return (
    <section id="projects" className="relative z-10 -mt-10 sm:-mt-12 md:-mt-14 rounded-t-[40px] sm:rounded-t-[50px] md:rounded-t-[60px] px-5 sm:px-8 md:px-10 pt-20 sm:pt-24 md:pt-32 pb-20" style={{ background: '#0C0C0C' }}>
      <FadeIn>
        <h2 className="hero-heading font-black uppercase leading-none tracking-tight text-center mb-16 sm:mb-20 md:mb-28" style={{ fontSize: 'clamp(3rem, 12vw, 160px)' }}>Project</h2>
      </FadeIn>
      <div ref={ref}>
        {projects.map((p, i) => <Card key={p.name} i={i} p={p} progress={scrollYProgress} total={projects.length} />)}
      </div>
    </section>
  );
}
