import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { toast } from "sonner";
import { Search } from "lucide-react";

const statuses = ["", "Requested", "Approved", "Paid", "Cancelled"];

export default function AdminRentals() {
  const [rentals, setRentals] = useState([]);
  const [status, setStatus] = useState("");
  const [q, setQ] = useState("");
  const load = async () => {
    const params = {};
    if (status) params.status = status;
    if (q) params.search = q;
    const { data } = await api.get("/admin/rentals", { params });
    setRentals(data);
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [status, q]);
  const approve = async (id) => { try { await api.patch(`/admin/rentals/${id}/approve`); toast.success("Approved"); load(); } catch (e) { toast.error(e.response?.data?.detail || "Failed"); } };
  return (
    <>
      <header className="topbar">
        <div><span className="eyebrow">ADMIN CONSOLE</span><h1>Rentals</h1></div>
        <div className="topbar-actions">
          <div className="search-wrap admin"><Search size={16} /><input data-testid="admin-rentals-search" value={q} onChange={e => setQ(e.target.value)} placeholder="Search tool or user" /></div>
          <select data-testid="admin-rentals-status" value={status} onChange={e => setStatus(e.target.value)} className="admin-select">
            {statuses.map(s => <option key={s} value={s}>{s || "All statuses"}</option>)}
          </select>
        </div>
      </header>
      <div className="admin-table" data-testid="admin-rentals-table">
        <div className="ar-head"><span>Tool</span><span>User</span><span>Dates</span><span>Days</span><span>Total</span><span>Status</span><span>Payment</span><span>Action</span></div>
        {rentals.map(r => (
          <div className="ar-row" key={r.id} data-testid={`admin-rental-row-${r.id}`}>
            <span><b>{r.tool_name}</b></span>
            <span>{r.renter_name}<br /><small>{r.user_email}</small></span>
            <span>{r.start_date} → {r.end_date}</span>
            <span>{r.days}</span>
            <span>₹{Number(r.total).toLocaleString()}</span>
            <span className={`request-status ${r.status.toLowerCase()}`}>{r.status}</span>
            <span className={`pay-pill ${String(r.payment_status || "unpaid").toLowerCase()}`}>{String(r.payment_status || "unpaid").replace("_", " ").toUpperCase()}</span>
            <span>{r.status === "Requested" && <button className="approve-btn" data-testid={`admin-approve-rental-${r.id}`} onClick={() => approve(r.id)}>Approve</button>}</span>
          </div>
        ))}
      </div>
    </>
  );
}
