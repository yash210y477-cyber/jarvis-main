import "./VoiceBar.css";

export default function VoiceBar() {
  return (
    <div className="voiceBar">

      <div className="mic">
        🎤
      </div>

      <div className="voiceContent">

        <span className="status">
          Listening...
        </span>

        <div className="wave">

          {Array.from({ length: 40 }).map((_, i) => (
            <span
              key={i}
              style={{
                animationDelay: `${i * 0.05}s`
              }}
            />
          ))}

        </div>

      </div>

    </div>
  );
}