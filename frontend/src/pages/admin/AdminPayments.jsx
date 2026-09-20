import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { Tractor, IndianRupee } from "lucide-react";

export default function AdminPayments() {
  const [payments, setPayments] = useState([]);
  useEffect(() => { api.get("/admin/payments").then(({ data }) => setPayments(data)); }, []);
  const collected = payments.filter(p => p.payment_status === "paid").reduce((s, p) => s + (p.amount || 0), 0);
  return (
    <>
      <header className="topbar">
        <div><span className="eyebrow">ADMIN CONSOLE</span><h1>Payments</h1></div>
        <div className="topbar-meta"><strong style={{ fontSize: 20 }}>₹{collected.toLocaleString()}</strong>&nbsp;collected&nbsp;· {payments.length} entries</div>
      </header>
      {payments.length === 0 ? (
        <div className="empty-state" data-testid="admin-payments-empty">
          <h3>No payments yet</h3>
          <p>Once a farmer completes checkout, the entry will appear here.</p>
        </div>
      ) : (
        <div className="payments-table" data-testid="admin-payments-table">
          <div className="pt-head"><span>Tool</span><span>Renter</span><span>Amount</span><span>Payment ID</span><span>When</span><span>Status</span></div>
          {payments.map(p => (
            <div className="pt-row" key={p.razorpay_payment_id}>
              <span className="pt-tool"><Tractor size={14} />{p.tool_name}</span>
              <span>{p.renter_name}</span>
              <span className="pt-amount"><IndianRupee size={12} />{Number(p.amount || 0).toLocaleString()}</span>
              <span className="pt-id" title={p.razorpay_payment_id}>{p.razorpay_payment_id}</span>
              <span>{p.paid_at ? new Date(p.paid_at).toLocaleString() : (p.failed_at ? new Date(p.failed_at).toLocaleString() : "—")}</span>
              <span className={`pt-status ${p.payment_status}`}>{p.payment_status}</span>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
