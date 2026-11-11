import HeroSection from './components/Hero';
import Dashboard from './components/Dashboard';
import Chat from './components/Chat';
import Panels from './components/Panels';
import { JarvisProvider } from './state';

export default function App() {
  return (
    <JarvisProvider>
      <main style={{ background: '#0C0C0C', overflowX: 'clip', fontFamily: "'Kanit', sans-serif" }}>
        <HeroSection />
        <Dashboard />
        <Chat />
        <Panels />
      </main>
    </JarvisProvider>
  );
}
