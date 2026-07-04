import { Sphere } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { useRef } from "react";

export default function EnergyCore() {

  const core = useRef();

  useFrame(({ clock }) => {

    const t = clock.getElapsedTime();

    core.current.scale.setScalar(1 + Math.sin(t * 2) * 0.08);

    core.current.rotation.y += 0.01;

    core.current.rotation.x += 0.003;

  });

  return (

    <Sphere
      ref={core}
      args={[0.45,128,128]}
    >

      <meshPhysicalMaterial

        color="#00E5FF"

        emissive="#00E5FF"

        emissiveIntensity={5}

        transmission={1}

        thickness={2}

        roughness={0}

        metalness={0.3}

        clearcoat={1}

      />

    </Sphere>

  );

}