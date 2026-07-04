import { Canvas } from "@react-three/fiber";
import { Stars } from "@react-three/drei";
import { EffectComposer, Bloom } from "@react-three/postprocessing";

import EnergyCore from "./EnergyCore";
import EnergyRing from "./EnergyRing";
import Particles from "./Particles";

export default function AIOrb() {
  return (
    <div className="orb">
      <Canvas
        camera={{
          position: [0, 0, 4],
          fov: 45,
        }}
      >
        {/* Lights */}
        <ambientLight intensity={1.2} />

        <pointLight
          position={[3, 3, 3]}
          intensity={25}
          color="#00E5FF"
        />

        <pointLight
          position={[-3, -3, -3]}
          intensity={12}
          color="#7C3AED"
        />

        {/* Space Background */}
        <Stars
          radius={20}
          depth={40}
          count={4000}
          factor={4}
          fade
          speed={1}
        />

        {/* Outer Ring */}
        <EnergyRing
          radius={1.8}
          tube={0.01}
          color="#00E5FF"
          speed={0.12}
        />

        {/* Middle Ring */}
        <EnergyRing
          radius={1.45}
          tube={0.015}
          color="#7C3AED"
          speed={0.28}
          direction={-1}
          rotation={[1, 0, 0]}
        />

        {/* Inner Ring */}
        <EnergyRing
          radius={1.1}
          tube={0.018}
          color="#00F5FF"
          speed={0.5}
          rotation={[0, 1, 0]}
        />

        {/* Energy Core */}
        <EnergyCore />

        {/* Floating Particles */}
        <Particles />

        {/* Glow */}
        <EffectComposer>
          <Bloom
            intensity={2.5}
            luminanceThreshold={0}
            luminanceSmoothing={0.9}
          />
        </EffectComposer>
      </Canvas>
    </div>
  );
}