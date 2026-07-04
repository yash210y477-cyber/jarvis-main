import "./Sidebar.css";
import { useState } from "react";
import { motion } from "framer-motion";

import {
  LayoutDashboard,
  Bot,
  Mic,
  Eye,
  Folder,
  Globe,
  Brain,
  Cpu,
  Settings,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

const menu = [
  { icon: LayoutDashboard, title: "Dashboard" },
  { icon: Bot, title: "AI Chat" },
  { icon: Mic, title: "Voice" },
  { icon: Eye, title: "Vision" },
  { icon: Folder, title: "Files" },
  { icon: Globe, title: "Browser" },
  { icon: Brain, title: "Memory" },
  { icon: Cpu, title: "Models" },
  { icon: Settings, title: "Settings" },
];

export default function Sidebar() {
  const [open, setOpen] = useState(true);

  return (
    <motion.div
      animate={{ width: open ? 250 : 80 }}
      transition={{ duration: 0.3 }}
      className="sidebar"
    >
      <div className="logo">
        <div className="circle">J</div>

        {open && <h2>JARVIS</h2>}
      </div>

      <div className="menu">
        {menu.map((item) => {
          const Icon = item.icon;

          return (
            <div className="item" key={item.title}>
              <Icon size={22} />

              {open && <span>{item.title}</span>}
            </div>
          );
        })}
      </div>

      <button className="toggle" onClick={() => setOpen(!open)}>
        {open ? <ChevronLeft /> : <ChevronRight />}
      </button>
    </motion.div>
  );
}