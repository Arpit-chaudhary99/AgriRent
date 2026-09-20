import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { PackageOpen, CheckCircle2, Users, CalendarDays, Wallet, XCircle } from "lucide-react";

export default function AdminDashboard() {
  const [stats, setStats] = useState(null);
  const [err, setErr] = useState("");
  useEffect(() => { api.get("/admin/stats").then(({ data }) => setStats(data)).catch(e => setErr(e.response?.data?.detail || "Could not load stats")); }, []);
  if (err) return <div className="empty-state">{err}</div>;
  if (!stats) return <div className="page-loader">Loading dashboard…</div>;
  const cards = [
    { icon: PackageOpen, label: "Total tools", value: stats.total_tools, tone: "leaf" },
    { icon: CheckCircle2, label: "Available now", value: stats.available_tools, tone: "leaf" },
    { icon: Users, label: "Total users", value: stats.total_users, tone: "sand" },
    { icon: CalendarDays, label: "Active rentals", value: stats.active_rentals, tone: "sand" },
    { icon: CheckCircle2, label: "Completed", value: stats.paid_rentals, tone: "leaf" },
    { icon: XCircle, label: "Cancelled", value: stats.cancelled_rentals, tone: "sand" },
    { icon: Wallet, label: "Revenue collected", value: `₹${Number(stats.total_revenue).toLocaleString()}`, tone: "wide" },
  ];
  return (
    <>
      <header className="topbar">
        <div>
          <span className="eyebrow">ADMIN CONSOLE</span>
          <h1>Overview</h1>
        </div>
      </header>
      <div className="stat-grid" data-testid="admin-stat-grid">
        {cards.map(({ icon: Icon, label, value, tone }) => (
          <div className={`stat-card ${tone}`} key={label} data-testid={`stat-${label.toLowerCase().replace(/\s+/g, "-")}`}>
            <div className="stat-icon"><Icon size={18} /></div>
            <span className="eyebrow">{label}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </div>
    </>
  );
}
