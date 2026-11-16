import { FadeIn, ContactButton, AnimatedText } from './ui';

const F = 'https://shrug-person-78902957.figma.site/_components/v2/ebb2b8f25d8e24d5f0a5ca8af4c950de81aa2fd7/';
const deco = [
  { src: 'moon_icon.11395d36.png', cls: 'w-[120px] sm:w-[160px] md:w-[210px] top-[4%] left-[1%] sm:left-[2%] md:left-[4%]', delay: 0.1, x: -80 },
  { src: 'p59_1.4659672e.png', cls: 'w-[100px] sm:w-[140px] md:w-[180px] bottom-[8%] left-[3%] sm:left-[6%] md:left-[10%]', delay: 0.25, x: -80 },
  { src: 'lego_icon-1.703bb594.png', cls: 'w-[120px] sm:w-[160px] md:w-[210px] top-[4%] right-[1%] sm:right-[2%] md:right-[4%]', delay: 0.15, x: 80 },
  { src: 'Group_134-1.2e04f3ce.png', cls: 'w-[130px] sm:w-[170px] md:w-[220px] bottom-[8%] right-[3%] sm:right-[6%] md:right-[10%]', delay: 0.3, x: 80 },
];

export default function AboutSection() {
  return (
    <section id="about" className="relative min-h-screen flex flex-col items-center justify-center px-5 sm:px-8 md:px-10 py-20 gap-16 sm:gap-20 md:gap-24" style={{ background: '#0C0C0C' }}>
      {deco.map((d) => (
        <FadeIn key={d.src} className={`absolute ${d.cls}`} delay={d.delay} x={d.x} y={0} duration={0.9}>
          <img src={F + d.src} alt="" className="w-full h-auto" />
        </FadeIn>
      ))}
      <div className="flex flex-col items-center gap-10 sm:gap-14 md:gap-16 relative z-[1]">
        <FadeIn delay={0} y={40}>
          <h2 className="hero-heading font-black uppercase leading-none tracking-tight text-center" style={{ fontSize: 'clamp(3rem, 12vw, 160px)' }}>About me</h2>
        </FadeIn>
        <AnimatedText
          text="With more than five years of experience in design, i focus on branding, web design, and user experience, i truly enjoy working with businesses that aim to stand out and present their best image. Let's build something incredible together!"
          className="text-[#D7E2EA] font-medium text-center leading-relaxed max-w-[560px]"
          style={{ fontSize: 'clamp(1rem, 2vw, 1.35rem)' }}
        />
      </div>
      <div className="relative z-[1]"><ContactButton /></div>
    </section>
  );
}
