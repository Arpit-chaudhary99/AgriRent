import axios from "axios";

export const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
export const api = axios.create({ baseURL: API, withCredentials: true });

export const setBearerToken = (token) => {
  if (token) api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
  else delete api.defaults.headers.common["Authorization"];
};

// Restore token from localStorage on module load
const saved = typeof window !== "undefined" ? window.localStorage.getItem("agrirent_session") : null;
if (saved) setBearerToken(saved);
