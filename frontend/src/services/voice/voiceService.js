const API = "http://127.0.0.1:8000";

// ----------------------------
// Single Voice Command
// ----------------------------
export async function startVoice() {

    const response = await fetch(`${API}/voice`, {
        method: "POST",
    });

    return await response.json();
}

// ----------------------------
// Continuous Voice Mode
// ----------------------------
export async function startLiveVoice() {

    const response = await fetch(`${API}/voice/live`, {
        method: "POST",
    });

    return await response.json();
}

// ----------------------------
// Stop Continuous Voice Mode
// ----------------------------
export async function stopVoice() {

    const response = await fetch(`${API}/voice/stop`, {
        method: "POST",
    });

    return await response.json();
}