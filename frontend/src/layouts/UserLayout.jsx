import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { Tractor, CalendarDays, UserCircle2, LogOut, Shield } from "lucide-react";
import { useState } from "react";

export default function UserLayout() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  const doLogout = async () => { await logout(); nav("/login", { replace: true }); };
  const nl = ({ isActive }) => `nav-item${isActive ? " active" : ""}`;

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileOpen ? "open" : ""}`}>
        <div className="brand">
          <div className="brand-mark"><Tractor size={22} /></div>
          <div><strong>AgriRent</strong><span>Equipment made easy</span></div>
        </div>
        <div className="side-label">Workspace</div>
        <NavLink to="/browse" className={nl} data-testid="nav-browse" onClick={() => setMobileOpen(false)}><Tractor size={18} />Browse tools</NavLink>
        <NavLink to="/rentals" className={nl} data-testid="nav-rentals" onClick={() => setMobileOpen(false)}><CalendarDays size={18} />My rentals</NavLink>
        <NavLink to="/profile" className={nl} data-testid="nav-profile" onClick={() => setMobileOpen(false)}><UserCircle2 size={18} />Profile</NavLink>
        {user?.role === "ADMIN" && (
          <NavLink to="/admin" className={nl} data-testid="nav-admin-panel"><Shield size={18} />Admin panel</NavLink>
        )}
        <div className="sidebar-foot">
          <div className="avatar">{user?.name?.[0] || "U"}</div>
          <div>
            <b>{user?.name}</b>
            <span>{user?.email}</span>
          </div>
          <button data-testid="logout-button" className="icon-btn" onClick={doLogout} title="Sign out"><LogOut size={16} /></button>
        </div>
      </aside>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
