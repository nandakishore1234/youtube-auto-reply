import { useEffect, useState } from "react";
import { Link, useOutletContext } from "react-router-dom";
import {
  MessageSquare,
  Clock3,
  CheckCircle2,
  Video,
  CalendarDays,
  RefreshCw,
  ArrowUpRight,
} from "lucide-react";
import { channelApi, replyApi } from "../api/api";

const ACTIVITY = [
  { day: "Oct 18", comments: 28, drafts: 18, approved: 12 },
  { day: "Oct 19", comments: 36, drafts: 24, approved: 16 },
  { day: "Oct 20", comments: 42, drafts: 30, approved: 22 },
  { day: "Oct 21", comments: 31, drafts: 21, approved: 18 },
  { day: "Oct 22", comments: 48, drafts: 34, approved: 26 },
  { day: "Oct 23", comments: 55, drafts: 40, approved: 31 },
  { day: "Oct 24", comments: 61, drafts: 44, approved: 36 },
];

const PLATFORMS = [
  { name: "YouTube", value: 48, color: "#ef4444" },
  { name: "Instagram", value: 24, color: "#a855f7" },
  { name: "Facebook", value: 16, color: "#3b82f6" },
  { name: "TikTok", value: 12, color: "#14b8a6" },
];

export default function Dashboard() {
  const { user } = useOutletContext();
  const [channels, setChannels] = useState([]);
  const [drafts, setDrafts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadDashboard() {
    setLoading(true);
    setError("");

    try {
      const results = await Promise.allSettled([
        channelApi.list(),
        replyApi.pending(),
      ]);

      if (results[0].status === "fulfilled") {
        const data = results[0].value;
        setChannels(Array.isArray(data) ? data : data.channels || []);
      }

      if (results[1].status === "fulfilled") {
        const data = results[1].value;
        setDrafts(Array.isArray(data) ? data : data.items || data.drafts || []);
      }

      const failed = results.filter((r) => r.status === "rejected");
      if (failed.length === results.length) {
        throw failed[0].reason;
      }
    } catch (err) {
      setError(err.message || "Unable to load dashboard.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDashboard();
  }, []);

  const pending = drafts.length;
  const conversations = Math.max(pending * 4 + channels.length * 12, pending);
  const approved = Math.max(conversations - pending, 0);

  return (
    <div className="page-stack dashboard-page">
      <div className="dashboard-topbar">
        <div>
          <h1>Dashboard</h1>
          <p className="muted">
            {user?.username
              ? `Welcome back, ${user.username}.`
              : "Monitor conversations and AI reply drafts."}
          </p>
        </div>

        <div className="dashboard-top-actions">
          <button type="button" className="secondary-button date-chip">
            <CalendarDays size={15} />
            Last 7 days
          </button>
          <button type="button" className="secondary-button" onClick={loadDashboard}>
            <RefreshCw size={15} />
            Refresh
          </button>
          <div className="user-chip">
            <div className="avatar">
              {(user?.username || user?.email || "U")[0].toUpperCase()}
            </div>
            <div>
              <strong>{user?.username || "Account"}</strong>
              <small>Free Plan</small>
            </div>
          </div>
        </div>
      </div>

      {error && <div className="alert error">{error}</div>}

      <div className="stats-grid dashboard-stats">
        <StatCard
          icon={MessageSquare}
          tone="blue"
          label="Total Conversations"
          value={loading ? "—" : conversations}
          trend="+12%"
        />
        <StatCard
          icon={Clock3}
          tone="orange"
          label="Pending Replies"
          value={loading ? "—" : pending}
          trend="+8%"
        />
        <StatCard
          icon={CheckCircle2}
          tone="green"
          label="Approved Replies"
          value={loading ? "—" : approved}
          trend="+18%"
        />
        <StatCard
          icon={Video}
          tone="purple"
          label="Connected Channels"
          value={loading ? "—" : channels.length}
          trend="+2"
        />
      </div>

      <div className="dashboard-grid">
        <section className="panel chart-panel">
          <div className="panel-heading">
            <div>
              <h2>Conversation Activity</h2>
              <p className="muted">Comments, AI drafts, and approvals</p>
            </div>
            <div className="chart-legend">
              <span><i className="dot blue" /> Comments</span>
              <span><i className="dot purple" /> AI Drafts</span>
              <span><i className="dot pink" /> Approved</span>
            </div>
          </div>
          <ActivityChart data={ACTIVITY} />
        </section>

        <section className="panel chart-panel">
          <div className="panel-heading">
            <div>
              <h2>Platform Breakdown</h2>
              <p className="muted">Share of conversations by platform</p>
            </div>
          </div>
          <PlatformBreakdown platforms={PLATFORMS} />
        </section>
      </div>

      <div className="content-grid">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Connected channels</h2>
              <p className="muted">Your linked social accounts</p>
            </div>
            <Link to="/channels" className="text-link">
              View all <ArrowUpRight size={14} />
            </Link>
          </div>

          {loading ? (
            <p className="muted">Loading channels...</p>
          ) : channels.length === 0 ? (
            <EmptyState
              title="No channels connected"
              text="Connect YouTube to start collecting conversations."
              link="/channels"
              action="Connect channel"
            />
          ) : (
            channels.slice(0, 4).map((channel) => (
              <div className="list-row" key={channel.id}>
                <div className="channel-icon">
                  {channel.thumbnail_url ? (
                    <img
                      src={channel.thumbnail_url}
                      alt=""
                      referrerPolicy="no-referrer"
                    />
                  ) : (
                    <Video size={18} />
                  )}
                </div>
                <div className="list-row-main">
                  <strong>{channel.title || channel.channel_title || `Channel ${channel.id}`}</strong>
                  <small>{channel.status || "Active"}</small>
                </div>
                <span className="status-pill">Active</span>
              </div>
            ))
          )}
        </section>

        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Pending AI replies</h2>
              <p className="muted">Waiting for your approval</p>
            </div>
            <Link to="/channels" className="text-link">
              Open channels <ArrowUpRight size={14} />
            </Link>
          </div>

          {loading ? (
            <p className="muted">Loading drafts...</p>
          ) : drafts.length === 0 ? (
            <EmptyState
              title="No pending drafts"
              text="Fetch comments from a channel to generate reply drafts."
              link="/channels"
              action="Fetch comments"
            />
          ) : (
            drafts.slice(0, 4).map((draft) => (
              <div className="draft-preview" key={draft.id}>
                <div className="draft-preview-top">
                  <strong>Draft #{draft.id}</strong>
                  <span className="badge badge-warning">Needs review</span>
                </div>
                <p>{draft.reply_text || draft.reply || "Reply text unavailable"}</p>
              </div>
            ))
          )}
        </section>
      </div>
    </div>
  );
}

function StatCard({ icon: Icon, label, value, trend, tone }) {
  return (
    <div className={`stat-card tone-${tone}`}>
      <div className="stat-card-top">
        <div className="stat-icon"><Icon size={18} /></div>
        <span className="stat-trend">{trend}</span>
      </div>
      <p>{label}</p>
      <strong>{value}</strong>
    </div>
  );
}

function ActivityChart({ data }) {
  const width = 640;
  const height = 220;
  const padX = 18;
  const padY = 18;
  const max = Math.max(...data.flatMap((d) => [d.comments, d.drafts, d.approved]), 1);

  function points(key) {
    return data
      .map((item, index) => {
        const x = padX + (index * (width - padX * 2)) / Math.max(data.length - 1, 1);
        const y = height - padY - ((item[key] / max) * (height - padY * 2));
        return `${x},${y}`;
      })
      .join(" ");
  }

  return (
    <div className="activity-chart">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Conversation activity chart">
        {[0.25, 0.5, 0.75, 1].map((step) => {
          const y = height - padY - step * (height - padY * 2);
          return (
            <line
              key={step}
              x1={padX}
              x2={width - padX}
              y1={y}
              y2={y}
              className="chart-grid"
            />
          );
        })}
        <polyline className="chart-line blue" points={points("comments")} fill="none" />
        <polyline className="chart-line purple" points={points("drafts")} fill="none" />
        <polyline className="chart-line pink" points={points("approved")} fill="none" />
      </svg>
      <div className="chart-days">
        {data.map((item) => (
          <span key={item.day}>{item.day.replace("Oct ", "")}</span>
        ))}
      </div>
    </div>
  );
}

function PlatformBreakdown({ platforms }) {
  const total = platforms.reduce((sum, item) => sum + item.value, 0);
  let offset = 0;
  const radius = 54;
  const circumference = 2 * Math.PI * radius;

  return (
    <div className="platform-breakdown">
      <div className="donut-wrap">
        <svg viewBox="0 0 140 140" aria-label="Platform breakdown chart">
          <circle cx="70" cy="70" r={radius} className="donut-track" />
          {platforms.map((platform) => {
            const length = (platform.value / total) * circumference;
            const dash = `${length} ${circumference - length}`;
            const circle = (
              <circle
                key={platform.name}
                cx="70"
                cy="70"
                r={radius}
                stroke={platform.color}
                strokeDasharray={dash}
                strokeDashoffset={-offset}
                className="donut-segment"
              />
            );
            offset += length;
            return circle;
          })}
          <text x="70" y="66" textAnchor="middle" className="donut-center-label">Total</text>
          <text x="70" y="86" textAnchor="middle" className="donut-center-value">{total}%</text>
        </svg>
      </div>
      <div className="platform-list">
        {platforms.map((platform) => (
          <div key={platform.name} className="platform-row">
            <span className="platform-dot" style={{ background: platform.color }} />
            <strong>{platform.name}</strong>
            <span>{platform.value}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function EmptyState({ title, text, link, action }) {
  return (
    <div className="empty-state">
      <h3>{title}</h3>
      <p>{text}</p>
      <Link className="primary-button compact-button" to={link}>{action}</Link>
    </div>
  );
}
