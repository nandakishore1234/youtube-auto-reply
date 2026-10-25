import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowRight,
  Check,
  Eye,
  EyeOff,
  LockKeyhole,
  Mail,
  MessageCircle,
  Sparkles,
} from "lucide-react";
import { authApi, saveToken } from "../api/api";

function ConversiqLogo({ compact = false }) {
  return (
    <div className={`conversiq-logo${compact ? " compact" : " hero"}`}>
      <img
        src="/conversiq-logo.png"
        alt="Conversiq"
        className="conversiq-logo-img"
      />
    </div>
  );
}

export default function Login() {
  const navigate = useNavigate();
  const [identity, setIdentity] = useState(
    () => window.localStorage.getItem("rememberedIdentity") || ""
  );
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(
    () => Boolean(window.localStorage.getItem("rememberedIdentity"))
  );
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      const result = await authApi.login({
        username_or_email: identity,
        password,
      });

      const token = result.access_token || result.token;

      if (!token) {
        throw new Error(
          "Login response did not contain an access token. Check your backend TokenResponse schema."
        );
      }

      saveToken(token);
      if (remember) {
        window.localStorage.setItem("rememberedIdentity", identity);
      } else {
        window.localStorage.removeItem("rememberedIdentity");
      }
      navigate("/", { replace: true });
    } catch (err) {
      setError(err.message || "Unable to sign in.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-intro">
        <div className="login-intro-content">
          <ConversiqLogo />

          <h1>
            Every conversation,
            <br />
            intelligently handled.
          </h1>
          <p>
            Manage, automate, and grow your audience across all your platforms
            with AI.
          </p>

          <div className="login-benefits">
            <div>
              <span><MessageCircle size={18} /></span>
              Connect your social platforms
            </div>
            <div>
              <span><Sparkles size={18} /></span>
              AI-generated reply drafts
            </div>
            <div>
              <span><Check size={18} strokeWidth={2.4} /></span>
              Review, approve and publish
            </div>
          </div>
        </div>
      </section>

      <section className="login-form-side">
        <div className="login-card">
          <ConversiqLogo compact />
          <div className="login-heading">
            <h2>Welcome back</h2>
            <p>Sign in to your account</p>
          </div>

          {error && <div className="alert error">{error}</div>}

          <form onSubmit={handleSubmit}>
            <div className="login-field">
              <label htmlFor="identity">Email or username</label>
              <div className="login-input">
                <span className="login-input-icon" aria-hidden="true">
                  <Mail size={16} strokeWidth={1.8} />
                </span>
                <input
                  id="identity"
                  autoComplete="username"
                  value={identity}
                  onChange={(e) => setIdentity(e.target.value)}
                  placeholder="you@example.com"
                  required
                />
              </div>
            </div>

            <div className="login-field">
              <label htmlFor="password">Password</label>
              <div className="login-input">
                <span className="login-input-icon" aria-hidden="true">
                  <LockKeyhole size={16} strokeWidth={1.8} />
                </span>
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  required
                />
                <button
                  className="password-toggle"
                  type="button"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? <EyeOff size={16} strokeWidth={1.8} /> : <Eye size={16} strokeWidth={1.8} />}
                </button>
              </div>
            </div>

            <div className="login-options">
              <label className="remember-me">
                <input
                  type="checkbox"
                  checked={remember}
                  onChange={(event) => setRemember(event.target.checked)}
                />
                <span>Remember me</span>
              </label>
              <button type="button" className="forgot-link">Forgot password?</button>
            </div>

            <button className="login-submit" disabled={loading}>
              <span>{loading ? "Signing in..." : "Sign in"}</span>
              {!loading && <ArrowRight size={17} />}
            </button>
          </form>

          <p className="login-register">
            New here? <Link to="/register">Create an account</Link>
          </p>
        </div>

        <p className="login-trust-note">
          <span>Secure</span>
          <i />
          <span>Private</span>
          <i />
          <span>AI-powered</span>
        </p>
      </section>
    </main>
  );
}
