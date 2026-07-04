import "./Header.css";
import { Bell, Cloud, Cpu, Search, Wifi } from "lucide-react";

export default function Header() {
  const time = new Date().toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <header className="header">

      <div className="searchBox">
        <Search size={18} />
        <input placeholder="Ask Jarvis anything..." />
      </div>

      <div className="status">

        <div className="badge">
          <Cpu size={16} />
          CPU 12%
        </div>

        <div className="badge">
          RAM 34%
        </div>

        <div className="badge online">
          Local AI
        </div>

        <div className="badge cloud">
          <Cloud size={15}/>
          Cloud
        </div>

        <div className="badge">
          <Wifi size={15}/>
        </div>

        <div className="clock">
          {time}
        </div>

        <Bell className="icon"/>

        <div className="avatar">
          J
        </div>

      </div>

    </header>
  );
}