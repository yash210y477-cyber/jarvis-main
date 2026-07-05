import "./ChatPanel.css";
import { Bot, SendHorizontal, User, Mic } from "lucide-react";
import { useState } from "react";

import { sendChatMessage } from "../../../services/api/chatService";
import { startVoice } from "../../../services/voice/voiceService";
import { executeAction } from "../../../services/actions/actionExecutor";

export default function ChatPanel() {
  const [messages, setMessages] = useState([
    {
      type: "bot",
      text: "Hello Yash 👋",
    },
    {
      type: "bot",
      text: "I'm JARVIS. How may I assist you today?",
    },
  ]);

  const [input, setInput] = useState("");

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage = input.trim();

    setMessages((prev) => [
      ...prev,
      {
        type: "user",
        text: userMessage,
      },
    ]);

    setInput("");

    try {
      const response = await sendChatMessage(userMessage);

      executeAction(response);

      setMessages((prev) => [
        ...prev,
        {
          type: "bot",
          text: response.message || response.response || "Done",
        },
      ]);
    } catch (error) {
      console.error(error);

      setMessages((prev) => [
        ...prev,
        {
          type: "bot",
          text: "Unable to connect to Jarvis Backend.",
        },
      ]);
    }
  };

  const handleVoice = async () => {
    try {
      const response = await startVoice();

      executeAction(response);

      setMessages((prev) => [
        ...prev,
        {
          type: "user",
          text: response.heard,
        },
        {
          type: "bot",
          text: response.message,
        },
      ]);
    } catch (error) {
      console.error(error);

      setMessages((prev) => [
        ...prev,
        {
          type: "bot",
          text: "Voice recognition failed.",
        },
      ]);
    }
  };

  return (
    <div className="chatContainer">
      <div className="chatHeader">
        <div className="jarvisLogo">
          <Bot size={24} />
        </div>

        <div>
          <h2>JARVIS</h2>
          <span>AI Assistant Online</span>
        </div>
      </div>

      <div className="chatBody">
        {messages.map((msg, index) => (
          <div
            key={index}
            className={msg.type === "user" ? "message user" : "message bot"}
          >
            <div className="avatar">
              {msg.type === "user" ? (
                <User size={18} />
              ) : (
                <Bot size={18} />
              )}
            </div>

            <div className="bubble">{msg.text}</div>
          </div>
        ))}
      </div>

      <div className="chatInput">
        <input
          placeholder="Ask Jarvis anything..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              handleSend();
            }
          }}
        />

        <button onClick={handleVoice}>
          <Mic size={20} />
        </button>

        <button onClick={handleSend}>
          <SendHorizontal size={20} />
        </button>
      </div>
    </div>
  );
}