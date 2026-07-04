import "./HUDRing.css";
import ring from "../../../assets/jarvis-ring.png";

import { useEffect, useRef } from "react";
import gsap from "gsap";

export default function HUDRing() {
  const ringRef = useRef(null);
  const haloRef = useRef(null);
  const glowRef = useRef(null);

  useEffect(() => {
    // Outer Ring Rotation
    gsap.to(ringRef.current, {
      rotation: 360,
      duration: 30,
      ease: "none",
      repeat: -1,
      transformOrigin: "50% 50%",
    });

    // Halo Rotation (Reverse)
    gsap.to(haloRef.current, {
      rotation: -360,
      duration: 18,
      ease: "none",
      repeat: -1,
      transformOrigin: "50% 50%",
    });

    // Core Glow Pulse
    gsap.to(glowRef.current, {
      scale: 1.2,
      opacity: 1,
      duration: 1.8,
      ease: "power1.inOut",
      yoyo: true,
      repeat: -1,
    });

    // Halo Pulse
    gsap.to(haloRef.current, {
      scale: 1.05,
      duration: 3,
      ease: "sine.inOut",
      yoyo: true,
      repeat: -1,
    });
  }, []);

  return (
    <div className="hud-ring">
      {/* Outer PNG Ring */}
      <img
        ref={ringRef}
        src={ring}
        alt="Jarvis HUD"
        className="ring"
      />

      {/* Animated Energy Halo */}
      <div
        ref={haloRef}
        className="energyHalo"
      ></div>

      {/* Center Glow */}
      <div
        ref={glowRef}
        className="coreGlow"
      ></div>
    </div>
  );
}