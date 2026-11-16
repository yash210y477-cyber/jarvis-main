import HeroSection from './components/Hero';
import MarqueeSection from './components/Marquee';
import AboutSection from './components/About';
import ServicesSection from './components/Services';
import ProjectsSection from './components/Projects';

export default function App() {
  return (
    <main style={{ background: '#0C0C0C', overflowX: 'clip', fontFamily: "'Kanit', sans-serif" }}>
      <HeroSection />
      <MarqueeSection />
      <AboutSection />
      <ServicesSection />
      <ProjectsSection />
    </main>
  );
}
