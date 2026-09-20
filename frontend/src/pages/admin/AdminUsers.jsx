import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { Search, Ban, Check, Shield } from "lucide-react";
import { toast } from "sonner";

export default function AdminUsers() {
  const [users, setUsers] = useState([]);
  const [q, setQ] = useState("");
  const load = async () => { const { data } = await api.get("/admin/users", { params: q ? { search: q } : {} }); setUsers(data); };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [q]);
  const toggleBlock = async (u) => {
    const next = !u.blocked;
    if (!window.confirm(`${next ? "Block" : "Unblock"} ${u.email}?`)) return;
    try { await api.patch(`/admin/users/${u.user_id}/block`, { blocked: next }); toast.success(next ? "User blocked" : "User unblocked"); load(); }
    catch (e) { toast.error(e.response?.data?.detail || "Failed"); }
  };
  return (
    <>
      <header className="topbar">
        <div><span className="eyebrow">ADMIN CONSOLE</span><h1>Users</h1></div>
        <div className="topbar-actions"><div className="search-wrap admin"><Search size={16} /><input data-testid="admin-users-search" value={q} onChange={e => setQ(e.target.value)} placeholder="Search by name or email" /></div></div>
      </header>
      <div className="admin-table" data-testid="admin-users-table">
        <div className="au-head"><span>User</span><span>Email</span><span>Role</span><span>Rentals</span><span>Spent</span><span>Status</span><span>Action</span></div>
        {users.map(u => (
          <div className="au-row" key={u.user_id} data-testid={`admin-user-row-${u.user_id}`}>
            <span className="au-user">
              {u.picture ? <img alt="" src={u.picture} /> : <span className="avatar">{u.name?.[0]}</span>}
              <b>{u.name}</b>
            </span>
            <span>{u.email}</span>
            <span className={`role-tag ${u.role.toLowerCase()}`}>{u.role === "ADMIN" ? <><Shield size={11} /> ADMIN</> : "USER"}</span>
            <span>{u.rental_count}</span>
            <span>₹{Number(u.total_spent || 0).toLocaleString()}</span>
            <span className={u.blocked ? "user-status blocked" : "user-status active"}>{u.blocked ? "Blocked" : "Active"}</span>
            <span>
              {u.role !== "ADMIN" && (
                <button className={`icon-btn ${u.blocked ? "" : "danger"}`} data-testid={`admin-toggle-block-${u.user_id}`} onClick={() => toggleBlock(u)} title={u.blocked ? "Unblock" : "Block"}>
                  {u.blocked ? <Check size={14} /> : <Ban size={14} />}
                </button>
              )}
            </span>
          </div>
        ))}
      </div>
    </>
  );
}
