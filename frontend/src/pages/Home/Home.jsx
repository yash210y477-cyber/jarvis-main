import "./Home.css";

import { useMemo } from "react";

import Background from "../../components/layout/Background/Background";

import ChatPanel from "../../components/chat/ChatPanel/ChatPanel";

import SystemCards from "../Dashboard/SystemCards/SystemCards";
import QuickActions from "../Dashboard/QuickActions/QuickActions";

import VoiceBar from "../../components/voice/VoiceBar/VoiceBar";

export default function Home() {

  const greeting = useMemo(() => {

    const hour = new Date().getHours();

    if (hour < 12) return "Good Morning";

    if (hour < 17) return "Good Afternoon";

    return "Good Evening";

  }, []);

  return (
    <>
      <Background />

      <div className="dashboard">

        {/* LEFT */}

        <section className="leftPanel">

          <div className="hero">

            <span className="hello">

              {greeting},

              <strong> Yash 👋</strong>

            </span>

            <h1>

              JARVIS

            </h1>

            <p>

              Just A Rather Very Intelligent System

            </p>

          </div>

          <QuickActions />

          <SystemCards />

          <div className="voiceSection">

            <VoiceBar />

          </div>

        </section>

        {/* RIGHT */}

        <aside className="rightPanel">

          <ChatPanel />

        </aside>

      </div>

    </>
  );
}