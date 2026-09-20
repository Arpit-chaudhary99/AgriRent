import { useAuth } from "../contexts/AuthContext";
import { Shield, LogOut } from "lucide-react";
import { useNavigate } from "react-router-dom";

export default function ProfilePage() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const doLogout = async () => { await logout(); nav("/login", { replace: true }); };

  if (!user) return null;
  const initials = (user.name || user.email || "U").split(" ").map(s => s[0]).join("").slice(0, 2).toUpperCase();

  return (
    <>
      <header className="topbar">
        <div>
          <span className="eyebrow">FARMER WORKSPACE</span>
          <h1>Your profile</h1>
        </div>
      </header>
      <div className="profile-card" data-testid="profile-card">
        <div className="profile-avatar">
          {user.picture ? <img src={user.picture} alt={user.name} /> : initials}
        </div>
        <div className="profile-info">
          <h2>{user.name}</h2>
          <p>{user.email}</p>
          <span className={`role-tag ${user.role.toLowerCase()}`}>{user.role === "ADMIN" ? <><Shield size={12} /> ADMIN</> : "USER"}</span>
        </div>
        <button className="cancel-btn" data-testid="profile-logout" onClick={doLogout}><LogOut size={14} /> Sign out</button>
      </div>
      <div className="profile-meta">
        <div><span className="eyebrow">Member since</span><strong>{new Date(user.created_at).toLocaleDateString()}</strong></div>
        <div><span className="eyebrow">Account status</span><strong>{user.blocked ? "Blocked" : "Active"}</strong></div>
        <div><span className="eyebrow">Sign-in method</span><strong>Google · Emergent Auth</strong></div>
      </div>
    </>
  );
}
