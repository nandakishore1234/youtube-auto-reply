import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  Bell,
  Check,
  ChevronDown,
  MoreHorizontal,
  Pencil,
  RefreshCw,
  Search,
  MessageSquareText,
  X,
} from "lucide-react";
import { Link, useNavigate, useOutletContext, useParams } from "react-router-dom";
import { channelApi, replyApi } from "../api/api";

function YoutubeIcon({ size = 14 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M23.5 6.2a3 3 0 0 0-2.1-2.1C19.5 3.5 12 3.5 12 3.5s-7.5 0-9.4.6A3 3 0 0 0 .5 6.2 31.5 31.5 0 0 0 0 12a31.5 31.5 0 0 0 .5 5.8 3 3 0 0 0 2.1 2.1c1.9.6 9.4.6 9.4.6s7.5 0 9.4-.6a3 3 0 0 0 2.1-2.1A31.5 31.5 0 0 0 24 12a31.5 31.5 0 0 0-.5-5.8zM9.8 15.5v-7l6.3 3.5-6.3 3.5z" />
    </svg>
  );
}

function initials(name = "U") {
  return String(name)
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() || "")
    .join("") || "U";
}

function videoThumb(videoId) {
  if (!videoId) return null;
  return `https://i.ytimg.com/vi/${videoId}/mqdefault.jpg`;
}

function normalizeList(data) {
  return Array.isArray(data) ? data : data.items || data.drafts || [];
}

export default function PendingReplies() {
  const { user } = useOutletContext() || {};
  const { channelId } = useParams();
  const navigate = useNavigate();
  const [channel, setChannel] = useState(null);
  const [pendingDrafts, setPendingDrafts] = useState([]);
  const [publishedDrafts, setPublishedDrafts] = useState([]);
  const [rejectedDrafts, setRejectedDrafts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [tab, setTab] = useState("pending");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(() => new Set());
  const [editingId, setEditingId] = useState(null);
  const [editText, setEditText] = useState("");
  const [confirmAction, setConfirmAction] = useState(null);
  const [expandedIds, setExpandedIds] = useState(() => new Set());

  const REPLY_PREVIEW_LIMIT = 160;

  function toggleExpanded(id) {
    setExpandedIds((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  useEffect(() => {
    if (!channelId) {
      navigate("/channels", { replace: true });
    }
  }, [channelId, navigate]);

  const loadDrafts = useCallback(async () => {
    if (!channelId) return;

    setLoading(true);
    setError("");

    try {
      const results = await Promise.allSettled([
        channelApi.get(channelId),
        replyApi.pending(channelId),
        replyApi.published(channelId),
        replyApi.rejected(channelId),
      ]);

      if (results[0].status === "fulfilled") {
        setChannel(results[0].value);
      } else {
        throw results[0].reason || new Error("Channel not found.");
      }

      if (results[1].status === "fulfilled") {
        setPendingDrafts(normalizeList(results[1].value));
      }
      if (results[2].status === "fulfilled") {
        setPublishedDrafts(normalizeList(results[2].value));
      }
      if (results[3].status === "fulfilled") {
        setRejectedDrafts(normalizeList(results[3].value));
      }

      const replyFailed = results.slice(1).filter((result) => result.status === "rejected");
      if (replyFailed.length === 3) {
        throw replyFailed[0].reason;
      }
      if (replyFailed.length) {
        setError("Some reply lists could not be loaded. Showing available data.");
      }
    } catch (err) {
      setError(err.message || "Unable to load reply drafts.");
    } finally {
      setLoading(false);
    }
  }, [channelId]);

  useEffect(() => {
    loadDrafts();
  }, [loadDrafts]);

  const activeDrafts = useMemo(() => {
    if (tab === "approved") return publishedDrafts;
    if (tab === "rejected") return rejectedDrafts;
    return pendingDrafts;
  }, [tab, pendingDrafts, publishedDrafts, rejectedDrafts]);

  const filteredDrafts = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return activeDrafts;
    return activeDrafts.filter((draft) => {
      const haystack = [
        draft.author,
        draft.comment_text,
        draft.reply_text,
        draft.channel_title,
        draft.intent,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return haystack.includes(needle);
    });
  }, [activeDrafts, query]);

  function toggleSelected(id) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function startEdit(draft) {
    setEditingId(draft.id);
    setEditText(draft.reply_text || draft.reply || "");
  }

  function cancelEdit() {
    setEditingId(null);
    setEditText("");
  }

  function saveEdit(draftId) {
    setPendingDrafts((current) =>
      current.map((draft) =>
        draft.id === draftId ? { ...draft, reply_text: editText } : draft
      )
    );
    setEditingId(null);
    setEditText("");
    setNotice(`Draft #${draftId} updated locally. Approve to publish.`);
  }

  function openConfirm(draft, action) {
    setConfirmAction({ draft, action });
  }

  function closeConfirm() {
    if (busyId !== null) return;
    setConfirmAction(null);
  }

  async function confirmAndRun() {
    if (!confirmAction) return;

    const { draft, action } = confirmAction;
    const label = action === "approve" ? "approve" : "reject";

    setBusyId(draft.id);
    setError("");
    setNotice("");

    try {
      if (action === "approve") {
        await replyApi.approve(draft.id);
      } else {
        await replyApi.reject(draft.id);
      }

      setNotice(
        action === "approve"
          ? `Draft #${draft.id} published to YouTube.`
          : `Draft #${draft.id} rejected.`
      );
      setSelected((current) => {
        const next = new Set(current);
        next.delete(draft.id);
        return next;
      });
      setConfirmAction(null);
      await loadDrafts();
    } catch (err) {
      setError(err.message || `Unable to ${label} draft.`);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="page-stack replies-page">
      <div className="dashboard-topbar">
        <div>
          <Link to="/channels" className="back-link">
            <ArrowLeft size={15} />
            Back to channels
          </Link>
          <div className="channel-page-heading">
            {channel?.thumbnail_url && (
              <img
                className="channel-page-avatar"
                src={channel.thumbnail_url}
                alt=""
                referrerPolicy="no-referrer"
              />
            )}
            <div>
              <h1>{channel?.title || "AI Reply Review"}</h1>
              <p className="muted">
                Review and approve AI-generated replies before publishing
              </p>
            </div>
          </div>
        </div>

        <div className="dashboard-top-actions">
          <button type="button" className="icon-button notify-btn" aria-label="Notifications">
            <Bell size={16} />
            <span className="notify-dot" />
          </button>
          <button
            type="button"
            className="secondary-button"
            onClick={loadDrafts}
            disabled={loading}
          >
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
            <ChevronDown size={14} className="chip-caret" />
          </div>
        </div>
      </div>

      {error && <div className="alert error">{error}</div>}
      {notice && <div className="alert success">{notice}</div>}

      <div className="replies-toolbar">
        <div className="reply-tabs">
          <button
            type="button"
            className={`reply-tab ${tab === "pending" ? "active" : ""}`}
            onClick={() => setTab("pending")}
          >
            Pending ({pendingDrafts.length})
          </button>
          <button
            type="button"
            className={`reply-tab ${tab === "approved" ? "active" : ""}`}
            onClick={() => setTab("approved")}
          >
            Approved ({publishedDrafts.length})
          </button>
          <button
            type="button"
            className={`reply-tab ${tab === "rejected" ? "active" : ""}`}
            onClick={() => setTab("rejected")}
          >
            Rejected ({rejectedDrafts.length})
          </button>
        </div>

        <div className="replies-filters">
          <label className="channels-search replies-search">
            <Search size={15} />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search comments..."
            />
          </label>
          <button type="button" className="secondary-button filter-chip">
            All Platforms <ChevronDown size={14} />
          </button>
          <button type="button" className="secondary-button filter-chip">
            Newest <ChevronDown size={14} />
          </button>
        </div>
      </div>

      {loading ? (
        <p className="muted">Loading drafts...</p>
      ) : filteredDrafts.length === 0 ? (
        <section className="panel">
          <div className="empty-state">
            <MessageSquareText size={34} />
            <h3>
              {activeDrafts.length === 0
                ? tab === "pending"
                  ? "You're all caught up"
                  : tab === "approved"
                    ? "No approved replies yet"
                    : "No rejected drafts yet"
                : "No matches"}
            </h3>
            <p>
              {activeDrafts.length === 0
                ? tab === "pending"
                  ? "No pending drafts. Fetch comments from a connected channel to generate more."
                  : tab === "approved"
                    ? "Approved means published to YouTube. They’ll show up here after you approve a draft."
                    : "Rejected drafts will appear here after you reject them."
                : "Try a different search term."}
            </p>
          </div>
        </section>
      ) : (
        <div className="draft-list">
          {filteredDrafts.map((draft) => {
            const author = draft.author || "YouTube viewer";
            const thumb = videoThumb(draft.youtube_video_id);
            const isEditing = editingId === draft.id && tab === "pending";
            const replyText = draft.reply_text || draft.reply || "Reply text unavailable";
            const isPending = tab === "pending";
            const isExpanded = expandedIds.has(draft.id);
            const needsViewMore = replyText.length > REPLY_PREVIEW_LIMIT;
            const shownReply =
              !isEditing && needsViewMore && !isExpanded
                ? `${replyText.slice(0, REPLY_PREVIEW_LIMIT).trimEnd()}...`
                : replyText;

            return (
              <article className="review-card modern-review-card" key={draft.id}>
                <div className="review-card-main">
                  {isPending && (
                    <label className="review-check">
                      <input
                        type="checkbox"
                        checked={selected.has(draft.id)}
                        onChange={() => toggleSelected(draft.id)}
                      />
                    </label>
                  )}

                  <div className="review-body">
                    <div className="review-content">
                      <div className="review-meta">
                        <div className="review-author">
                          <div className="review-avatar">{initials(author)}</div>
                          <div>
                            <strong>{author}</strong>
                            <small>
                              <span className="platform-mini youtube">
                                <YoutubeIcon size={12} />
                              </span>
                              {draft.channel_title || "YouTube"} · Draft #{draft.id}
                              {tab === "approved" && " · Published"}
                              {tab === "rejected" && " · Rejected"}
                            </small>
                          </div>
                        </div>
                        {thumb && (
                          <a
                            className="review-thumb"
                            href={`https://www.youtube.com/watch?v=${draft.youtube_video_id}`}
                            target="_blank"
                            rel="noreferrer"
                            title="Open video"
                          >
                            <img src={thumb} alt="" referrerPolicy="no-referrer" />
                          </a>
                        )}
                      </div>

                      <p className="review-comment">
                        {draft.comment_text || "Original comment unavailable"}
                      </p>

                      <div className="ai-reply-box">
                        <div className="ai-reply-label">
                          {tab === "approved" ? "Published Reply" : "AI Suggested Reply"}
                        </div>
                        {isEditing ? (
                          <textarea
                            className="ai-reply-editor"
                            value={editText}
                            onChange={(event) => setEditText(event.target.value)}
                            rows={4}
                          />
                        ) : (
                          <>
                            <p className={isExpanded ? "expanded" : ""}>{shownReply}</p>
                            {needsViewMore && (
                              <button
                                type="button"
                                className="view-more-btn"
                                onClick={() => toggleExpanded(draft.id)}
                              >
                                {isExpanded ? "Read less" : "Read more"}
                              </button>
                            )}
                          </>
                        )}
                      </div>

                      {draft.review_reason && (
                        <p className="review-reason">
                          <strong>Review note:</strong> {draft.review_reason}
                        </p>
                      )}
                    </div>

                    {isPending ? (
                      <div className="review-actions">
                        {isEditing ? (
                          <>
                            <button
                              className="approve-btn"
                              type="button"
                              onClick={() => saveEdit(draft.id)}
                            >
                              <Check size={16} /> Save
                            </button>
                            <button
                              className="edit-btn"
                              type="button"
                              onClick={cancelEdit}
                            >
                              Cancel
                            </button>
                          </>
                        ) : (
                          <>
                            <button
                              className="approve-btn"
                              type="button"
                              disabled={busyId !== null}
                              onClick={() => openConfirm(draft, "approve")}
                            >
                              <Check size={16} />
                              {busyId === draft.id ? "Publishing..." : "Approve"}
                            </button>
                            <button
                              className="edit-btn"
                              type="button"
                              disabled={busyId !== null}
                              onClick={() => startEdit(draft)}
                            >
                              <Pencil size={15} /> Edit
                            </button>
                            <button
                              className="reject-btn"
                              type="button"
                              disabled={busyId !== null}
                              onClick={() => openConfirm(draft, "reject")}
                            >
                              <X size={16} /> Reject
                            </button>
                            <button
                              className="icon-button more-btn"
                              type="button"
                              aria-label="More actions"
                            >
                              <MoreHorizontal size={16} />
                            </button>
                          </>
                        )}
                      </div>
                    ) : (
                      <div className="review-actions">
                        <span className={`status-pill ${tab === "rejected" ? "rejected" : ""}`}>
                          {tab === "approved" ? "Published on YouTube" : "Rejected"}
                        </span>
                        {tab === "approved" && draft.youtube_video_id && (
                          <a
                            className="edit-btn"
                            href={`https://www.youtube.com/watch?v=${draft.youtube_video_id}`}
                            target="_blank"
                            rel="noreferrer"
                          >
                            View on YouTube
                          </a>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}

      {confirmAction && (
        <div
          className="confirm-overlay"
          onClick={closeConfirm}
          role="presentation"
        >
          <div
            className="confirm-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="confirm-title"
            onClick={(event) => event.stopPropagation()}
          >
            <button
              type="button"
              className="confirm-close"
              onClick={closeConfirm}
              disabled={busyId !== null}
              aria-label="Close"
            >
              <X size={16} />
            </button>

            <div
              className={`confirm-badge ${
                confirmAction.action === "approve" ? "approve" : "reject"
              }`}
            >
              {confirmAction.action === "approve" ? (
                <Check size={18} />
              ) : (
                <X size={18} />
              )}
            </div>

            <h2 id="confirm-title">
              {confirmAction.action === "approve"
                ? "Publish this reply?"
                : "Reject this draft?"}
            </h2>
            <p className="confirm-subtitle">
              {confirmAction.action === "approve"
                ? "This will post the AI reply publicly on YouTube."
                : "This draft will be discarded and won’t be published."}
            </p>

            <div className="confirm-preview">
              <div className="confirm-preview-row">
                <div className="review-avatar">
                  {initials(confirmAction.draft.author || "U")}
                </div>
                <div>
                  <strong>{confirmAction.draft.author || "YouTube viewer"}</strong>
                  <small>
                    {confirmAction.draft.channel_title || "YouTube"} · Draft #
                    {confirmAction.draft.id}
                  </small>
                </div>
              </div>

              <div className="confirm-block">
                <span>Original comment</span>
                <p>
                  {confirmAction.draft.comment_text ||
                    "Original comment unavailable"}
                </p>
              </div>

              <div className="confirm-block reply">
                <span>AI Suggested Reply</span>
                <p>
                  {confirmAction.draft.reply_text ||
                    confirmAction.draft.reply ||
                    "Reply text unavailable"}
                </p>
              </div>
            </div>

            <div className="confirm-actions">
              <button
                type="button"
                className="secondary-button"
                onClick={closeConfirm}
                disabled={busyId !== null}
              >
                Cancel
              </button>
              <button
                type="button"
                className={
                  confirmAction.action === "approve" ? "approve-btn" : "reject-btn"
                }
                onClick={confirmAndRun}
                disabled={busyId !== null}
              >
                {busyId === confirmAction.draft.id ? (
                  confirmAction.action === "approve" ? "Publishing..." : "Rejecting..."
                ) : confirmAction.action === "approve" ? (
                  <>
                    <Check size={16} /> Approve & Publish
                  </>
                ) : (
                  <>
                    <X size={16} /> Reject Draft
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
