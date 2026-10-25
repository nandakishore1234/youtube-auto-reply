
const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export function getToken() {
  return localStorage.getItem("access_token");
}

export function saveToken(token) {
  localStorage.setItem("access_token", token);
}

export function clearToken() {
  localStorage.removeItem("access_token");
}

export async function apiRequest(path, options = {}) {
  const token = getToken();

  const headers = {
    ...(options.body ? { "Content-Type": "application/json" } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    credentials: "include",
  });

  if (response.status === 204) return null;

  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  
    if (!response.ok) {
      let message = `Request failed (${response.status})`;
  
      if (typeof data === "string") {
        message = data;
      } else if (Array.isArray(data.detail)) {
        message = data.detail
          .map((item) => item.msg || JSON.stringify(item))
          .join(", ");
      } else if (typeof data.detail === "string") {
        message = data.detail;
      } else if (data.detail != null) {
        message = JSON.stringify(data.detail);
      } else if (data.message) {
        message = data.message;
      }
  
      throw new Error(message);
    }
  

  return data;
}

export const authApi = {
  register: (payload) =>
    apiRequest("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  login: (payload) =>
    apiRequest("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  me: () => apiRequest("/api/v1/auth/me"),
};

export const channelApi = {
  list: () => apiRequest("/api/v1/channels"),

  get: (channelId) => apiRequest(`/api/v1/channels/${channelId}`),

  fetchComments: (channelId) =>
    apiRequest(`/api/v1/channels/${channelId}/comments/fetch`, {
      method: "POST",
    }),

  startOAuth: () =>
    apiRequest("/api/v1/youtube/oauth/start-url"),
};

function withChannelQuery(path, channelId) {
  if (!channelId) return path;
  return `${path}?channel_id=${encodeURIComponent(channelId)}`;
}

export const replyApi = {
  pending: (channelId) =>
    apiRequest(withChannelQuery("/api/v1/replies/pending", channelId)),
  published: (channelId) =>
    apiRequest(withChannelQuery("/api/v1/replies/published", channelId)),
  rejected: (channelId) =>
    apiRequest(withChannelQuery("/api/v1/replies/rejected", channelId)),

  approve: (draftId) =>
    apiRequest(`/api/v1/replies/${draftId}/approve`, {
      method: "POST",
    }),

  reject: (draftId) =>
    apiRequest(`/api/v1/replies/${draftId}/reject`, {
      method: "POST",
    }),
};
