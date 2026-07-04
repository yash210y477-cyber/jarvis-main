import "./MainLayout.css";

import Sidebar from "../components/layout/Sidebar/Sidebar";
import Header from "../components/layout/Header/Header";

export default function MainLayout({ children }) {
  return (
    <div className="layout">

      <Sidebar />

      <div className="layout-main">

        <Header />

        <div className="layout-content">

          {children}

        </div>

      </div>

    </div>
  );
}