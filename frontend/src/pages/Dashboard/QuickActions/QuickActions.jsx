import "./QuickActions.css";

import {
  Globe,
  Code2,
  FolderOpen,
  Terminal,
  Calculator,
  Monitor,
  Music,
  Settings,
} from "lucide-react";

import {
  openChrome,
  openVSCode,
  openExplorer,
  openTerminal,
} from "../../../services/electron/electron";

export default function QuickActions() {
  const actions = [
    {
      title: "Chrome",
      subtitle: "Browse Internet",
      icon: Globe,
      action: openChrome,
    },
    {
      title: "VS Code",
      subtitle: "Write Code",
      icon: Code2,
      action: openVSCode,
    },
    {
      title: "Explorer",
      subtitle: "Manage Files",
      icon: FolderOpen,
      action: openExplorer,
    },
    {
      title: "Terminal",
      subtitle: "Run Commands",
      icon: Terminal,
      action: openTerminal,
    },
    {
      title: "Calculator",
      subtitle: "Quick Math",
      icon: Calculator,
      action: () => {},
    },
    {
      title: "Monitor",
      subtitle: "System Info",
      icon: Monitor,
      action: () => {},
    },
    {
      title: "Music",
      subtitle: "Play Songs",
      icon: Music,
      action: () => {},
    },
    {
      title: "Settings",
      subtitle: "Preferences",
      icon: Settings,
      action: () => {},
    },
  ];

  return (
    <div className="quickActions">
      {actions.map((item, index) => {
        const Icon = item.icon;

        return (
          <div
            key={index}
            className="actionCard"
            onClick={item.action}
          >
            <div className="actionTop">
              <div className="iconBox">
                <Icon size={32} />
              </div>
            </div>

            <div className="actionBottom">
              <h3>{item.title}</h3>
              <p>{item.subtitle}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}