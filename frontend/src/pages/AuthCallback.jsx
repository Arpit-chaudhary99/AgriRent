import { useEffect, useRef } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { api, setBearerToken } from "../lib/api";
import { useAuth } from "../contexts/AuthContext";

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
export default function AuthCallback() {
  const nav = useNavigate();
  const location = useLocation();
  const { setUser, checkAuth } = useAuth();
  const processed = useRef(false);

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;
    const hash = location.hash || window.location.hash || "";
    const m = /session_id=([^&]+)/.exec(hash);
    if (!m) {
      // No session in URL — try normal auth check
      checkAuth?.().then(() => nav("/browse", { replace: true }));
      return;
    }
    const session_id = decodeURIComponent(m[1]);
    (async () => {
      try {
        const { data } = await api.post("/auth/session", { session_id });
        if (data.session_token) {
          window.localStorage.setItem("agrirent_session", data.session_token);
          setBearerToken(data.session_token);
        }
        setUser(data.user);
        // Clean the fragment
        window.history.replaceState(null, "", window.location.pathname);
        nav(data.user.role === "ADMIN" ? "/admin" : "/browse", { replace: true, state: { user: data.user } });
      } catch (e) {
        nav("/login", { replace: true, state: { error: e?.response?.data?.detail || "Sign-in failed" } });
      }
    })();
  }, [location, nav, setUser, checkAuth]);

  return <div className="page-loader" data-testid="auth-callback-loader">Signing you in…</div>;
}
