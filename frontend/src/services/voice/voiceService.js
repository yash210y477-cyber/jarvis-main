const API_URL = "http://127.0.0.1:8000/voice";

export async function startVoice() {
  const response = await fetch(API_URL, {
    method: "POST",
  });

  if (!response.ok) {
    throw new Error("Voice API failed");
  }

  return await response.json();
}