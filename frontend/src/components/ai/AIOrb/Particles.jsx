import { Sparkles } from "@react-three/drei";

export default function Particles() {
  return (
    <Sparkles
      count={800}
      scale={6}
      size={3}
      speed={0.4}
      color="#00E5FF"
    />
  );
}