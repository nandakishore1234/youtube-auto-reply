import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { RefreshCw, Plus, Search, MoreVertical } from "lucide-react";
import { channelApi } from "../api/api";

const OAUTH_PENDING_KEY = "youtube_oauth_pending";

function YoutubeIcon({ size = 22 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M23.5 6.2a3 3 0 0 0-2.1-2.1C19.5 3.5 12 3.5 12 3.5s-7.5 0-9.4.6A3 3 0 0 0 .5 6.2 31.5 31.5 0 0 0 0 12a31.5 31.5 0 0 0 .5 5.8 3 3 0 0 0 2.1 2.1c1.9.6 9.4.6 9.4.6s7.5 0 9.4-.6a3 3 0 0 0 2.1-2.1A31.5 31.5 0 0 0 24 12a31.5 31.5 0 0 0-.5-5.8zM9.8 15.5v-7l6.3 3.5-6.3 3.5z" />
    </svg>
  );
}

function InstagramIcon({ size = 22 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M7 2h10a5 5 0 0 1 5 5v10a5 5 0 0 1-5 5H7a5 5 0 0 1-5-5V7a5 5 0 0 1 5-5zm10 2H7a3 3 0 0 0-3 3v10a3 3 0 0 0 3 3h10a3 3 0 0 0 3-3V7a3 3 0 0 0-3-3zm-5 3.5A4.5 4.5 0 1 1 7.5 12 4.5 4.5 0 0 1 12 7.5zm0 2A2.5 2.5 0 1 0 14.5 12 2.5 2.5 0 0 0 12 9.5zm5.2-3.1a1.1 1.1 0 1 1-1.1 1.1 1.1 1.1 0 0 1 1.1-1.1z" />
    </svg>
  );
}

function FacebookIcon({ size = 22 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M14 8h3V5h-3c-2.8 0-5 2.2-5 5v2H7v3h2v7h3v-7h3l1-3h-4v-2c0-.6.4-1 1-1z" />
    </svg>
  );
}

function TikTokIcon({ size = 22 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M19.59 6.69a4.83 4.83 0 0 1-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 0 1-2.88 2.5 2.89 2.89 0 0 1-2.89-2.89 2.89 2.89 0 0 1 2.89-2.89c.28 0 .55.04.81.1v-3.5a6.37 6.37 0 0 0-.81-.05A6.34 6.34 0 0 0 3.16 15.3a6.34 6.34 0 0 0 6.34 6.34 6.34 6.34 0 0 0 6.34-6.34V8.87a8.2 8.2 0 0 0 4.76 1.52V6.94a4.85 4.85 0 0 1-1.01-.25z" />
    </svg>
  );
}

const PLATFORMS = [
  {
    id: "youtube",
    name: "YouTube",
    status: "Ready to connect",
    connectable: true,
    icon: YoutubeIcon,
    tone: "youtube",
  },
  {
    id: "instagram",
    name: "Instagram",
    status: "Coming soon",
    connectable: false,
    icon: InstagramIcon,
    tone: "instagram",
  },
  {
    id: "facebook",
    name: "Facebook",
    status: "Coming soon",
    connectable: false,
    icon: FacebookIcon,
    tone: "facebook",
  },
  {
    id: "tiktok",
    name: "TikTok",
    status: "Coming soon",
    connectable: false,
    icon: TikTokIcon,
    tone: "tiktok",
  },
  {
    id: "others",
    name: "Others",
    status: "Request access",
    connectable: false,
    icon: Plus,
    tone: "others",
  },
];

function formatCount(value) {
  if (value == null || value === "") return "—";
  const number = Number(value);
  if (Number.isNaN(number)) return String(value);
  if (number >= 1000000) return `${(number / 1000000).toFixed(1)}M`;
  if (number >= 1000) return `${(number / 1000).toFixed(1)}K`;
  return number.toLocaleString();
}

function formatRelative(value) {
  if (!value) return "Not fetched";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  const diffMs = Date.now() - date.getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins} min ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ago`;
  const days = Math.floor(hours / 24);
  return `${days} day${days === 1 ? "" : "s"} ago`;
}

export default function Channels() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [channels, setChannels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState(null);
  const [connecting, setConnecting] = useState(false);
  const [connectFailed, setConnectFailed] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [query, setQuery] = useState("");

  const loadChannels = useCallback(async () => {
    setLoading(true);

    try {
      const data = await channelApi.list();
      setChannels(Array.isArray(data) ? data : data.channels || []);
    } catch (err) {
      setError(err.message || "Unable to load channels.");
    } finally {
      setLoading(false);
    }
  }, []);

  const markConnectCancelled = useCallback(() => {
    window.sessionStorage.removeItem(OAUTH_PENDING_KEY);
    setConnecting(false);
    setConnectFailed(true);
    setNotice("");
    setError(
      "YouTube connection failed or was cancelled. Click Connect to try again."
    );
  }, []);

  useEffect(() => {
    loadChannels();
  }, [loadChannels]);

  useEffect(() => {
    const status = searchParams.get("youtube");

    if (status === "connected") {
      window.sessionStorage.removeItem(OAUTH_PENDING_KEY);
      setConnecting(false);
      setConnectFailed(false);
      setError("");
      setNotice("YouTube channel connected successfully.");
      setSearchParams({}, { replace: true });
      return;
    }

    if (status === "denied" || status === "failed") {
      markConnectCancelled();
      setSearchParams({}, { replace: true });
      return;
    }

    if (window.sessionStorage.getItem(OAUTH_PENDING_KEY)) {
      markConnectCancelled();
    } else {
      setConnecting(false);
    }
  }, [searchParams, setSearchParams, markConnectCancelled]);

  useEffect(() => {
    function handlePageShow(event) {
      if (!event.persisted) return;
      setConnecting(false);
      if (window.sessionStorage.getItem(OAUTH_PENDING_KEY)) {
        markConnectCancelled();
      }
    }

    function handleVisibility() {
      if (document.visibilityState !== "visible") return;
      if (!window.sessionStorage.getItem(OAUTH_PENDING_KEY)) return;
      // User came back without finishing Google OAuth.
      if (!window.location.href.includes("accounts.google.com")) {
        markConnectCancelled();
      }
    }

    window.addEventListener("pageshow", handlePageShow);
    document.addEventListener("visibilitychange", handleVisibility);
    return () => {
      window.removeEventListener("pageshow", handlePageShow);
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, [markConnectCancelled]);

  const filteredChannels = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return channels;
    return channels.filter((channel) => {
      const title = (channel.title || channel.channel_title || "").toLowerCase();
      const handle = (
        channel.handle ||
        channel.custom_url ||
        channel.channel_id ||
        ""
      ).toLowerCase();
      return title.includes(needle) || handle.includes(needle);
    });
  }, [channels, query]);

  async function connectChannel() {
    setConnecting(true);
    setConnectFailed(false);
    setError("");
    setNotice("");

    try {
      const result = await channelApi.startOAuth();
      if (!result.authorization_url) {
        throw new Error("The backend did not return an authorization URL.");
      }
      window.sessionStorage.setItem(OAUTH_PENDING_KEY, String(Date.now()));
      window.location.assign(result.authorization_url);
    } catch (err) {
      window.sessionStorage.removeItem(OAUTH_PENDING_KEY);
      setConnectFailed(true);
      setError(err.message || "Unable to start YouTube connection.");
      setConnecting(false);
    }
  }

  async function fetchComments(channel) {
    setBusyId(channel.id);
    setError("");
    setNotice("");

    try {
      const result = await channelApi.fetchComments(channel.id);
      setNotice(
        `Fetch finished. Videos checked: ${result.videos_checked ?? "—"}; comments fetched: ${result.comments_fetched ?? "—"}; drafts processed: ${result.comments_processed ?? "—"}; failed: ${result.failed ?? "—"}.`
      );
      await loadChannels();
    } catch (err) {
      setError(err.message || "Unable to fetch comments.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="page-stack channels-page">
      <div className="page-heading">
        <div>
          <h1>Channels</h1>
          <p className="muted">Connect and manage your social media channels</p>
        </div>
      </div>

      {error && <div className="alert error">{error}</div>}
      {notice && <div className="alert success">{notice}</div>}

      <section className="platform-connect-grid">
        {PLATFORMS.map((platform) => {
          const Icon = platform.icon;
          return (
            <article className={`platform-card tone-${platform.tone}`} key={platform.id}>
              <div className="platform-card-icon">
                <Icon size={22} />
              </div>
              <h3>{platform.name}</h3>
              <p>
                {platform.connectable
                  ? connecting
                    ? "Connecting to Google..."
                    : connectFailed
                      ? "Connection failed"
                      : platform.status
                  : platform.status}
              </p>
              {platform.connectable ? (
                <button
                  type="button"
                  className={`platform-connect-btn${connectFailed && !connecting ? " failed-btn" : ""}`}
                  onClick={connectChannel}
                  disabled={connecting}
                >
                  {connecting
                    ? "Connecting..."
                    : connectFailed
                      ? "Try Again"
                      : "Connect"}
                </button>
              ) : (
                <button type="button" className="platform-connect-btn muted-btn" disabled>
                  Coming Soon
                </button>
              )}
            </article>
          );
        })}
      </section>

      <section className="panel channels-table-panel">
        <div className="panel-heading channels-table-heading">
          <h2>Connected Channels ({channels.length})</h2>
          <div className="channels-toolbar">
            <label className="channels-search">
              <Search size={15} />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search channels..."
              />
            </label>
            <button
              type="button"
              className="icon-button"
              onClick={loadChannels}
              disabled={loading}
              aria-label="Refresh channels"
            >
              <RefreshCw size={16} />
            </button>
          </div>
        </div>

        {loading ? (
          <p className="muted">Loading channels...</p>
        ) : filteredChannels.length === 0 ? (
          <div className="empty-state">
            <YoutubeIcon size={34} />
            <h3>{channels.length === 0 ? "No channels connected" : "No matches"}</h3>
            <p>
              {channels.length === 0
                ? "Connect YouTube to import your channels and start fetching comments."
                : "Try a different search term."}
            </p>
            {channels.length === 0 && (
              <button className="primary-button compact-button" onClick={connectChannel}>
                Connect YouTube
              </button>
            )}
          </div>
        ) : (
          <div className="channels-table-wrap">
            <table className="channels-table">
              <thead>
                <tr>
                  <th>Channel</th>
                  <th>Platform</th>
                  <th>Followers</th>
                  <th>Total Comments</th>
                  <th>Last Fetched</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredChannels.map((channel) => {
                  const title =
                    channel.title || channel.channel_title || `Channel ${channel.id}`;
                  const handle =
                    channel.handle ||
                    channel.custom_url ||
                    channel.channel_id ||
                    `id-${channel.id}`;

                  return (
                    <tr
                      key={channel.id}
                      className="channel-row-clickable"
                      onClick={() => navigate(`/channels/${channel.id}/replies`)}
                    >
                      <td>
                        <div className="channel-cell">
                          <div className="channel-icon">
                            {channel.thumbnail_url ? (
                              <img
                                src={channel.thumbnail_url}
                                alt=""
                                referrerPolicy="no-referrer"
                              />
                            ) : (
                              <YoutubeIcon size={18} />
                            )}
                          </div>
                          <div>
                            <strong>{title}</strong>
                            <small>@{String(handle).replace(/^@/, "")}</small>
                          </div>
                        </div>
                      </td>
                      <td>
                        <span className="platform-chip youtube">
                          <YoutubeIcon size={14} />
                          YouTube
                        </span>
                      </td>
                      <td>{formatCount(channel.subscriber_count ?? channel.followers)}</td>
                      <td>{formatCount(channel.comment_count ?? channel.total_comments)}</td>
                      <td>{formatRelative(channel.last_fetched_at ?? channel.updated_at)}</td>
                      <td>
                        <span className="status-pill">
                          {channel.status || "Active"}
                        </span>
                      </td>
                      <td>
                        <div className="table-actions" onClick={(event) => event.stopPropagation()}>
                          <button
                            type="button"
                            className="secondary-button fetch-btn"
                            onClick={() => fetchComments(channel)}
                            disabled={busyId !== null}
                          >
                            <RefreshCw size={14} />
                            {busyId === channel.id ? "Fetching..." : "Fetch Comments"}
                          </button>
                          <button
                            type="button"
                            className="secondary-button fetch-btn"
                            onClick={() => navigate(`/channels/${channel.id}/replies`)}
                          >
                            AI Replies
                          </button>
                          <button type="button" className="icon-button" aria-label="More actions">
                            <MoreVertical size={16} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
