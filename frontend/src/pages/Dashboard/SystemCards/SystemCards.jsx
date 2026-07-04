import "./SystemCards.css";

import { useEffect, useState } from "react";

import {
  Cpu,
  MemoryStick,
  HardDrive,
  Wifi,
} from "lucide-react";

import { getSystemInfo } from "../../../services/electron/electron";

export default function SystemCards() {
  const [system, setSystem] = useState({
    cpu: 0,
    ram: 0,
    storage: 0,
    network: "Offline",
  });

  useEffect(() => {
    const loadData = async () => {
      const data = await getSystemInfo();

      if (data) {
        setSystem(data);
      }
    };

    loadData();

    const timer = setInterval(loadData, 1000);

    return () => clearInterval(timer);
  }, []);

  const cards = [
    {
      title: "CPU Usage",
      value: `${system.cpu}%`,
      progress: system.cpu,
      icon: Cpu,
    },
    {
      title: "Memory",
      value: `${system.ram}%`,
      progress: system.ram,
      icon: MemoryStick,
    },
    {
      title: "Storage",
      value: `${system.storage}%`,
      progress: system.storage,
      icon: HardDrive,
    },
    {
      title: "Network",
      value: system.network,
      progress: system.network === "Online" ? 100 : 0,
      icon: Wifi,
    },
  ];

  return (
    <div className="systemGrid">
      {cards.map((item, index) => {
        const Icon = item.icon;

        return (
          <div
            key={index}
            className="systemCard"
          >
            <div className="systemHeader">

              <div className="systemIcon">

                <Icon size={24} />

              </div>

              <div>

                <h4>{item.title}</h4>

                <h2>{item.value}</h2>

              </div>

            </div>

            <div className="progressBar">

              <div
                className="progressFill"
                style={{
                  width: `${item.progress}%`,
                }}
              ></div>

            </div>

          </div>
        );
      })}
    </div>
  );
}