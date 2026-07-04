import { Sphere, Float } from "@react-three/drei";

export default function CoreScene() {
  return (
    <>
      <Float speed={2} rotationIntensity={1} floatIntensity={1}>
        <Sphere args={[1, 128, 128]}>
          <meshPhysicalMaterial
            color="#00E5FF"
            emissive="#00E5FF"
            emissiveIntensity={3}
            roughness={0}
            metalness={1}
            clearcoat={1}
            transmission={0.4}
          />
        </Sphere>
      </Float>
    </>
  );
}