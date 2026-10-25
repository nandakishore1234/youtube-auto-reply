
import { useEffect, useState } from "react";
import {
  Navigate,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";

import { authApi, clearToken, getToken } from "./api/api";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import Channels from "./pages/Channels";
import PendingReplies from "./pages/PendingReplies";

function ProtectedLayout() {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(true);
  const location = useLocation();

  useEffect(() => {
    let cancelled = false;

    async function verifySession() {
      if (!getToken()) {
        setChecking(false);
        return;
      }

      try {
        const currentUser = await authApi.me();
        if (!cancelled) setUser(currentUser);
      } catch {
        clearToken();
      } finally {
        if (!cancelled) setChecking(false);
      }
    }

    verifySession();

    return () => {
      cancelled = true;
    };
  }, [location.pathname]);

  if (checking) {
    return <div className="loading-screen">Checking your session...</div>;
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <Layout user={user} />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      <Route element={<ProtectedLayout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/channels" element={<Channels />} />
        <Route path="/channels/:channelId/replies" element={<PendingReplies />} />
        <Route path="/replies" element={<Navigate to="/channels" replace />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
