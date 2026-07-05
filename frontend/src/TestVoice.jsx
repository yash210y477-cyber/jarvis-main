import { processVoice } from "./services/voice/voiceService";

export default function TestVoice() {

  async function test() {

    const result = await processVoice("Open Terminal");

    console.log(result);

  }

  return (
    <button onClick={test}>
      Test Voice
    </button>
  );
}