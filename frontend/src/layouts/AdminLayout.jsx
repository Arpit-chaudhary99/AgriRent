import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { LayoutDashboard, PackageOpen, Users, CalendarDays, Receipt, LogOut, ArrowLeft, Tractor } from "lucide-react";

export default function AdminLayout() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const doLogout = async () => { await logout(); nav("/login", { replace: true }); };
  const nl = ({ isActive }) => `nav-item${isActive ? " active" : ""}`;

  return (
    <div className="app-shell admin-shell">
      <aside className="sidebar admin-sidebar">
        <div className="brand">
          <div className="brand-mark admin-mark"><LayoutDashboard size={20} /></div>
          <div><strong>AgriRent</strong><span>Admin console</span></div>
        </div>
        <div className="side-label">Overview</div>
        <NavLink to="/admin" end className={nl} data-testid="admin-nav-dashboard"><LayoutDashboard size={18} />Dashboard</NavLink>
        <div className="side-label" style={{ marginTop: 18 }}>Manage</div>
        <NavLink to="/admin/tools" className={nl} data-testid="admin-nav-tools"><PackageOpen size={18} />Tools</NavLink>
        <NavLink to="/admin/users" className={nl} data-testid="admin-nav-users"><Users size={18} />Users</NavLink>
        <NavLink to="/admin/rentals" className={nl} data-testid="admin-nav-rentals"><CalendarDays size={18} />Rentals</NavLink>
        <NavLink to="/admin/payments" className={nl} data-testid="admin-nav-payments"><Receipt size={18} />Payments</NavLink>
        <div style={{ marginTop: 24 }}>
          <NavLink to="/browse" className="nav-item" data-testid="admin-back-to-app"><ArrowLeft size={18} />Back to farmer view</NavLink>
        </div>
        <div className="sidebar-foot">
          <div className="avatar admin-avatar">{user?.name?.[0] || "A"}</div>
          <div>
            <b>{user?.name}</b>
            <span>{user?.email}</span>
          </div>
          <button data-testid="admin-logout" className="icon-btn" onClick={doLogout} title="Sign out"><LogOut size={16} /></button>
        </div>
      </aside>
      <main className="main-content admin-main">
        <Outlet />
      </main>
    </div>
  );
}
