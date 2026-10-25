import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  MessagesSquare,
  Video,
  BarChart3,
  Zap,
  Settings,
  UserRound,
  KeyRound,
  LogOut,
  Crown,
  Menu,
  X,
} from "lucide-react";
import { clearToken } from "../api/api";

const primaryLinks = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/channels", label: "Channels", icon: Video },
];

const upcoming = [
  { label: "Conversations", icon: MessagesSquare },
  { label: "Analytics", icon: BarChart3 },
  { label: "Automation", icon: Zap },
];

export default function Layout({ user }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    function onKeyDown(event) {
      if (event.key === "Escape") setSidebarOpen(false);
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  useEffect(() => {
    document.body.style.overflow = sidebarOpen ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [sidebarOpen]);

  function logout() {
    clearToken();
    navigate("/login", { replace: true });
  }

  return (
    <div className={`app-shell${sidebarOpen ? " sidebar-open" : ""}`}>
      <button
        type="button"
        className="mobile-menu-btn"
        aria-label={sidebarOpen ? "Close menu" : "Open menu"}
        aria-expanded={sidebarOpen}
        onClick={() => setSidebarOpen((open) => !open)}
      >
        {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
      </button>

      <div
        className="sidebar-backdrop"
        onClick={() => setSidebarOpen(false)}
        aria-hidden="true"
      />

      <aside className="sidebar">
        <div className="sidebar-top">
          <NavLink to="/" className="brand" end onClick={() => setSidebarOpen(false)}>
            <img src="/conversiq-logo.png" alt="Conversiq" className="brand-logo" />
          </NavLink>
          <button
            type="button"
            className="sidebar-close-btn"
            aria-label="Close menu"
            onClick={() => setSidebarOpen(false)}
          >
            <X size={18} />
          </button>
        </div>

        <nav className="nav-links">
          {primaryLinks.map(({ to, label, icon: Icon, end }, index) => (
            <NavLink
              key={`${label}-${index}`}
              to={to}
              end={end}
              className={({ isActive }) =>
                `nav-link ${isActive ? "active" : ""}`
              }
              onClick={() => setSidebarOpen(false)}
            >
              <Icon size={18} />
              <span>{label}</span>
            </NavLink>
          ))}

          {upcoming.map(({ label, icon: Icon }) => (
            <button key={label} type="button" className="nav-link nav-link-muted" disabled>
              <Icon size={18} />
              <span>{label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <button type="button" className="nav-link nav-link-muted" disabled>
            <Settings size={18} />
            <span>Settings</span>
          </button>
          <button type="button" className="nav-link nav-link-muted" disabled>
            <UserRound size={18} />
            <span>Profile</span>
          </button>
          <button type="button" className="nav-link nav-link-muted" disabled>
            <KeyRound size={18} />
            <span>API Keys</span>
          </button>

          <div className="upgrade-card">
            <div className="upgrade-icon"><Crown size={18} /></div>
            <strong>Upgrade to Pro</strong>
            <p>Unlock unlimited AI replies and automation.</p>
            <button type="button" className="upgrade-button">Upgrade</button>
          </div>

          <button className="nav-link logout-button" onClick={logout}>
            <LogOut size={18} /> Sign out
          </button>
        </div>
      </aside>

      <main className="main-area">
        <Outlet context={{ user }} />
      </main>
    </div>
  );
}
