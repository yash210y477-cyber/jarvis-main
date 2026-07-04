import "./ChatPanel.css";
import { Bot, SendHorizontal, User } from "lucide-react";
import { useState } from "react";

import { sendMessage as chatAPI } from "../../../services/api/chatApi";
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

  const [loading, setLoading] = useState(false);

  async function sendMessage() {
    if (!input.trim() || loading) return;

    const userMessage = input;

    setMessages((prev) => [
      ...prev,
      {
        type: "user",
        text: userMessage,
      },
    ]);

    setInput("");

    setLoading(true);

    try {
      const response = await chatAPI(userMessage);

      executeAction(response);

      let reply = "";

      if (response.provider === "gemini") {
        reply = response.response;
      } else {
        reply = response.message;
      }

      setMessages((prev) => [
        ...prev,
        {
          type: "bot",
          text: reply,
        },
      ]);
    } catch (error) {
      console.error(error);

      setMessages((prev) => [
        ...prev,
        {
          type: "bot",
          text: "Sorry, I couldn't process your request.",
        },
      ]);
    }

    setLoading(false);
  }

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
            className={
              msg.type === "user"
                ? "message user"
                : "message bot"
            }
          >
            <div className="avatar">
              {msg.type === "user" ? (
                <User size={18} />
              ) : (
                <Bot size={18} />
              )}
            </div>

            <div className="bubble">
              {msg.text}
            </div>
          </div>
        ))}

        {loading && (
          <div className="message bot">
            <div className="avatar">
              <Bot size={18} />
            </div>

            <div className="bubble">
              Thinking...
            </div>
          </div>
        )}
      </div>

      <div className="chatInput">
        <input
          placeholder="Ask Jarvis anything..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              sendMessage();
            }
          }}
        />

        <button
          onClick={sendMessage}
          disabled={loading}
        >
          <SendHorizontal size={20} />
        </button>
      </div>
    </div>
  );
}