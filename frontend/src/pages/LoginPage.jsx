import { Tractor } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { Navigate } from "react-router-dom";

export default function LoginPage() {
  const { user, loading } = useAuth();
  if (loading) return <div className="page-loader">Loading…</div>;
  if (user) return <Navigate to={user.role === "ADMIN" ? "/admin" : "/browse"} replace />;

  // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
  const startGoogleLogin = () => {
    const redirectUrl = window.location.origin + "/dashboard";
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  return (
    <div className="login-shell" data-testid="login-page">
      <div className="login-hero">
        <div className="login-brand">
          <div className="brand-mark"><Tractor size={22} /></div>
          <div>
            <strong>AgriRent Pro</strong>
            <span>Equipment made easy</span>
          </div>
        </div>
        <h1>Good tools.<br /><i>Better harvests.</i></h1>
        <p>Rent dependable farming equipment from trusted local owners, exactly when your fields need it.</p>
        <ul className="login-checklist">
          <li>Browse tractors, harvesters, tillers and drills nearby</li>
          <li>Pick your dates and pay securely with UPI on Razorpay</li>
          <li>Track every rental and payment in one place</li>
        </ul>
      </div>
      <div className="login-card">
        <span className="eyebrow">SIGN IN</span>
        <h2>Welcome back</h2>
        <p className="login-sub">Sign in with your Google account to continue. New here? Signing in creates your farmer account automatically.</p>
        <button data-testid="google-login-button" className="google-btn" onClick={startGoogleLogin}>
          <svg width="18" height="18" viewBox="0 0 48 48"><path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3c-1.6 4.6-6 8-11.3 8-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.9 1.2 8 3.1l5.7-5.7C34.6 6.1 29.6 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.3-.4-3.5z"/><path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.9 1.2 8 3.1l5.7-5.7C34.6 6.1 29.6 4 24 4 16.3 4 9.6 8.3 6.3 14.7z"/><path fill="#4CAF50" d="M24 44c5.5 0 10.4-2.1 14.1-5.5l-6.5-5.5c-2 1.4-4.6 2.3-7.6 2.3-5.3 0-9.7-3.4-11.3-8l-6.5 5C9.5 39.6 16.2 44 24 44z"/><path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.4-2.3 4.4-4.3 5.8l6.5 5.5C41 35.8 44 30.4 44 24c0-1.3-.1-2.3-.4-3.5z"/></svg>
          Continue with Google
        </button>
        <p className="login-note">Secured by Emergent Auth · Your Google email is used only for sign-in.</p>
      </div>
    </div>
  );
}
