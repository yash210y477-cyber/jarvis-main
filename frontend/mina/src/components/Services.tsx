import { FadeIn } from './ui';

const services = [
  ['3D Modeling', 'Creation of detailed objects, characters, or environments tailored to specific client needs, ideal for games, products, and visualizations.'],
  ['Rendering', 'High-quality, photorealistic renders that showcase designs with custom lighting, textures, and materials to bring concepts to life.'],
  ['Motion Design', 'Dynamic animations and motion graphics that add energy and storytelling to brands, products, and digital experiences.'],
  ['Branding', 'Crafting cohesive visual identities — from logos to full brand systems — that communicate a clear and memorable presence.'],
  ['Web Design', 'Designing clean, modern, and conversion-focused websites with attention to layout, typography, and user experience.'],
];

export default function ServicesSection() {
  return (
    <section id="price" className="rounded-t-[40px] sm:rounded-t-[50px] md:rounded-t-[60px] px-5 sm:px-8 md:px-10 py-20 sm:py-24 md:py-32" style={{ background: '#FFFFFF' }}>
      <FadeIn>
        <h2 className="font-black uppercase text-center mb-16 sm:mb-20 md:mb-28" style={{ color: '#0C0C0C', fontSize: 'clamp(3rem, 12vw, 160px)' }}>Services</h2>
      </FadeIn>
      <div className="max-w-5xl mx-auto">
        {services.map(([name, desc], i) => (
          <FadeIn key={name} delay={i * 0.1}>
            <div className="flex items-start gap-4 sm:gap-8 md:gap-12 py-8 sm:py-10 md:py-12" style={{ borderTop: '1px solid rgba(12, 12, 12, 0.15)', borderBottom: i === services.length - 1 ? '1px solid rgba(12, 12, 12, 0.15)' : undefined }}>
              <span className="font-black leading-none" style={{ color: '#0C0C0C', fontSize: 'clamp(3rem, 10vw, 140px)' }}>{String(i + 1).padStart(2, '0')}</span>
              <div className="flex flex-col gap-3" style={{ color: '#0C0C0C' }}>
                <h3 className="font-medium uppercase" style={{ fontSize: 'clamp(1rem, 2.2vw, 2.1rem)' }}>{name}</h3>
                <p className="font-light leading-relaxed max-w-2xl" style={{ fontSize: 'clamp(0.85rem, 1.6vw, 1.25rem)', opacity: 0.6 }}>{desc}</p>
              </div>
            </div>
          </FadeIn>
        ))}
      </div>
    </section>
  );
}
