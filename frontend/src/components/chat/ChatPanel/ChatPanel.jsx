import "./ChatPanel.css";
import { Bot, SendHorizontal, User, Mic, MicOff } from "lucide-react";
import { useState, useEffect } from "react";

import { sendChatMessage } from "../../../services/api/chatService";
import {
    startLiveVoice,
    stopVoice
} from "../../../services/voice/voiceService";

import { executeAction } from "../../../services/actions/actionExecutor";

export default function ChatPanel() {

    const [messages, setMessages] = useState([
        {
            type: "bot",
            text: "Hello Yash 👋"
        },
        {
            type: "bot",
            text: "I'm JARVIS. How may I assist you today?"
        }
    ]);

    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [voiceRunning, setVoiceRunning] = useState(false);

    useEffect(() => {

        return () => {

            stopVoice().catch(() => {});

        };

    }, []);

    //-----------------------------------
    // Send Message
    //-----------------------------------

    const handleSend = async () => {

        if (!input.trim() || loading) return;

        const text = input.trim();

        setMessages(prev => [
            ...prev,
            {
                type: "user",
                text
            }
        ]);

        setInput("");
        setLoading(true);

        try {

            const response = await sendChatMessage(text);

            executeAction(response);

            const reply =
                response.response ||
                response.message ||
                response.data?.response ||
                response.data?.message ||
                "Done";

            setMessages(prev => [
                ...prev,
                {
                    type: "bot",
                    text: reply
                }
            ]);

        } catch {

            setMessages(prev => [
                ...prev,
                {
                    type: "bot",
                    text: "Unable to connect to Jarvis."
                }
            ]);

        } finally {

            setLoading(false);

        }

    };

    //-----------------------------------
    // Toggle Voice
    //-----------------------------------

    const handleVoice = async () => {

        if (loading) return;

        if (!voiceRunning) {

            setVoiceRunning(true);

            setMessages(prev => [
                ...prev,
                {
                    type: "bot",
                    text: "🎤 Voice Mode Started..."
                }
            ]);

            try {

                const response = await startLiveVoice();

                console.log(response);

            } catch {

                setMessages(prev => [
                    ...prev,
                    {
                        type: "bot",
                        text: "Voice Error."
                    }
                ]);

                setVoiceRunning(false);

            }

        } else {

            try {

                await stopVoice();

            } catch (e) {

                console.log(e);

            }

            setVoiceRunning(false);

            setMessages(prev => [
                ...prev,
                {
                    type: "bot",
                    text: "🛑 Voice Mode Stopped."
                }
            ]);

        }

    };

    //-----------------------------------
    // UI
    //-----------------------------------

    return (

        <div className="chatContainer">

            <div className="chatHeader">

                <div className="jarvisLogo">
                    <Bot size={24}/>
                </div>

                <div>

                    <h2>JARVIS</h2>

                    <span>
                        {
                            voiceRunning
                                ? "🎤 Listening..."
                                : "AI Assistant Online"
                        }
                    </span>

                </div>

            </div>

            <div className="chatBody">

                {
                    messages.map((msg, index) => (

                        <div
                            key={index}
                            className={
                                msg.type === "user"
                                    ? "message user"
                                    : "message bot"
                            }
                        >

                            <div className="avatar">

                                {
                                    msg.type === "user"
                                        ? <User size={18}/>
                                        : <Bot size={18}/>
                                }

                            </div>

                            <div className="bubble">
                                {msg.text}
                            </div>

                        </div>

                    ))
                }

            </div>

            <div className="chatInput">

                <input
                    placeholder="Ask Jarvis anything..."
                    value={input}
                    disabled={voiceRunning}
                    onChange={(e)=>setInput(e.target.value)}
                    onKeyDown={(e)=>{

                        if(e.key==="Enter"){

                            handleSend();

                        }

                    }}
                />

                <button onClick={handleVoice}>

                    {
                        voiceRunning
                            ? <MicOff size={20}/>
                            : <Mic size={20}/>
                    }

                </button>

                <button
                    onClick={handleSend}
                    disabled={voiceRunning}
                >

                    <SendHorizontal size={20}/>

                </button>

            </div>

        </div>

    );

}