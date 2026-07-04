import "./Particles.css";

export default function Particles() {

  const particles = Array.from({ length: 40 });

  return (
    <div className="particles">

      {particles.map((_, i) => (
        <span
          key={i}
          style={{
            left: Math.random() * 100 + "%",
            animationDelay: Math.random() * 6 + "s",
            animationDuration: 4 + Math.random() * 6 + "s"
          }}
        />
      ))}

    </div>
  );
}