import { Torus } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { useRef } from "react";

export default function EnergyRing({
  radius,
  tube,
  color,
  speed = 0.2,
  direction = 1,
  rotation = [0, 0, 0],
}) {

  const ref = useRef();

  useFrame((_, delta) => {
    if (!ref.current) return;

    ref.current.rotation.x += delta * speed * direction;
    ref.current.rotation.y += delta * speed * direction;
    ref.current.rotation.z += delta * speed * 0.4 * direction;
  });

  return (
    <group ref={ref} rotation={rotation}>
      <Torus args={[radius, tube, 32, 200]}>
        <meshPhysicalMaterial
          color={color}
          emissive={color}
          emissiveIntensity={4}
          transmission={0.9}
          roughness={0}
          metalness={1}
          clearcoat={1}
        />
      </Torus>
    </group>
  );
}