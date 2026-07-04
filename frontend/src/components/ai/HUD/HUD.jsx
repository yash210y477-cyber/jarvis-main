import "./HUD.css";

export default function HUD() {
  return (
    <div className="hud">

      <div className="outerRing"></div>

      <div className="middleRing"></div>

      <div className="innerRing"></div>

      <div className="scanLine"></div>

      <div className="pulseRing"></div>

      <div className="centerDot"></div>

      {/* Circular Ticks */}
      {Array.from({ length: 72 }).map((_, i) => (
        <span
          key={i}
          className="tick"
          style={{
            transform: `rotate(${i * 5}deg) translateY(-330px)`
          }}
        />
      ))}

      {/* Orbit Dots */}
      <div className="orbit orbit1">
        <div className="planet"></div>
      </div>

      <div className="orbit orbit2">
        <div className="planet purple"></div>
      </div>

      <div className="orbit orbit3">
        <div className="planet small"></div>
      </div>

    </div>
  );
}