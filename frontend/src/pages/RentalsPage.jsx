import { useEffect, useState } from "react";
import { Tractor, Clock3, CheckCircle2, XCircle, PackageOpen, ChevronRight } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { api, API } from "../lib/api";
import { toast } from "sonner";
import { useAuth } from "../contexts/AuthContext";

export default function RentalsPage() {
  const { user } = useAuth();
  const [rentals, setRentals] = useState([]);
  const [payments, setPayments] = useState([]);
  const [methods, setMethods] = useState(null);
  const [tab, setTab] = useState("active"); // active | completed | cancelled
  const nav = useNavigate();

  const load = async () => {
    try {
      const [r, p, m] = await Promise.all([
        api.get("/rentals"),
        api.get("/payments/history"),
        api.get("/payments/methods").catch(() => ({ data: null })),
      ]);
      setRentals(r.data); setPayments(p.data); setMethods(m.data);
    } catch (e) { toast.error("Could not load rentals"); }
  };
  useEffect(() => { load(); }, []);

  const filtered = rentals.filter(r => {
    if (tab === "active") return ["Requested", "Approved", "Paid"].includes(r.status);
    if (tab === "completed") return r.status === "Paid";
    if (tab === "cancelled") return r.status === "Cancelled";
    return true;
  });

  const cancelRental = async (id) => {
    if (!window.confirm("Cancel this rental request?")) return;
    try {
      await api.post(`/rentals/${id}/cancel`);
      toast.success("Rental cancelled");
      load();
    } catch (e) { toast.error(e.response?.data?.detail || "Unable to cancel"); }
  };

  const payRental = async (rental) => {
    try {
      const script = document.createElement("script");
      script.src = "https://checkout.razorpay.com/v1/checkout.js";
      document.body.appendChild(script);
      await new Promise((resolve, reject) => { script.onload = resolve; script.onerror = () => reject(new Error("Could not load Razorpay Checkout")); });
      const { data: order } = await api.post(`/payments/order?rental_id=${rental.id}`);
      const options = {
        key: order.key_id,
        amount: order.amount,
        currency: order.currency,
        name: "AgriRent Pro",
        description: `Rental payment · ${rental.tool_name}`,
        order_id: order.id,
        method: { upi: true, card: true, netbanking: true, wallet: true },
        prefill: { name: user?.name, email: user?.email, contact: "9999999999" },
        notes: { rental_id: rental.id },
        theme: { color: "#2d6a4f" },
        modal: {
          confirm_close: true,
          ondismiss: async () => {
            try { await api.post("/payments/failed", { rental_id: rental.id, razorpay_order_id: order.id, reason: "user_cancelled" }); } catch {}
            toast("Payment cancelled — you can retry any time");
            load();
          },
        },
        handler: async (response) => {
          try {
            await api.post("/payments/verify", {
              rental_id: rental.id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_order_id: response.razorpay_order_id,
              razorpay_signature: response.razorpay_signature,
            });
            toast.success("Payment verified — rental confirmed");
            load();
          } catch (e) { toast.error(e.response?.data?.detail || "Payment verification failed — please retry"); load(); }
        },
      };
      const checkout = new window.Razorpay(options);
      checkout.on("payment.failed", async (resp) => {
        const err = resp?.error || {};
        try { await api.post("/payments/failed", { rental_id: rental.id, razorpay_order_id: err.metadata?.order_id || order.id, razorpay_payment_id: err.metadata?.payment_id, code: err.code, description: err.description, reason: err.reason }); } catch {}
        toast.error(err.description || "Payment failed — please retry"); load();
      });
      checkout.open();
    } catch (e) { toast.error(e.message || "Unable to open checkout"); }
  };

  return (
    <>
      <header className="topbar">
        <div>
          <span className="eyebrow">FARMER WORKSPACE</span>
          <h1>Your rental activity</h1>
        </div>
        <div className="topbar-meta"><div className="status-dot"></div><span>{rentals.length} total</span></div>
      </header>

      {methods && !methods.upi_collect && (
        <div className="upi-warn" data-testid="upi-disabled-banner">
          <b>UPI is disabled on your Razorpay test account.</b>
          <span>Open Razorpay Dashboard → Account & Settings → Payment Methods → enable <em>UPI</em>. Once enabled, refresh — UPI will appear alongside Cards, Netbanking and Wallet.</span>
        </div>
      )}

      <div className="tab-strip">
        {[["active", "Active"], ["completed", "Completed"], ["cancelled", "Cancelled"]].map(([k, l]) => (
          <button key={k} className={`tab ${tab === k ? "on" : ""}`} data-testid={`rentals-tab-${k}`} onClick={() => setTab(k)}>{l}</button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <div className="empty-state">
          <PackageOpen size={34} />
          <h3>No {tab} rentals</h3>
          <p>Browse available equipment and your requests will show up here.</p>
          <button className="rent-btn" data-testid="empty-browse-button" onClick={() => nav("/browse")}>Browse tools <ChevronRight size={16} /></button>
        </div>
      ) : (
        <div className="rental-list">
          {filtered.map(r => (
            <div className="rental-row" key={r.id} data-testid={`rental-row-${r.id}`}>
              <div className="rental-icon"><Tractor size={20} /></div>
              <div className="rental-main">
                <b>{r.tool_name}</b>
                <span>{r.start_date} → {r.end_date} · {r.days} day{r.days > 1 ? "s" : ""}</span>
              </div>
              <strong>₹{r.total.toLocaleString()}</strong>
              <span className={`request-status ${r.status.toLowerCase()}`}>
                {r.status === "Paid" ? <CheckCircle2 size={13} /> : r.status === "Cancelled" ? <XCircle size={13} /> : <Clock3 size={13} />}
                {r.status}
              </span>
              {r.status === "Approved" && r.payment_status !== "paid" && (
                (r.payment_status === "PAYMENT_PENDING" || r.payment_status === "failed")
                  ? <button className="pay-btn retry" data-testid={`retry-rental-${r.id}`} onClick={() => payRental(r)}>Retry Payment</button>
                  : <button className="pay-btn" data-testid={`pay-rental-${r.id}`} onClick={() => payRental(r)}>Pay via UPI</button>
              )}
              {r.status === "Requested" && (
                <button className="cancel-btn" data-testid={`cancel-rental-${r.id}`} onClick={() => cancelRental(r.id)}>Cancel</button>
              )}
              {r.payment_status && r.payment_status !== "unpaid" && r.payment_status !== "created" && (
                <span className={`pay-pill ${String(r.payment_status).toLowerCase()}`} data-testid={`pay-pill-${r.id}`}>
                  {String(r.payment_status).replace("_", " ").toUpperCase()}
                </span>
              )}
            </div>
          ))}
        </div>
      )}

      {payments.length > 0 && (
        <>
          <div className="section-head" style={{ marginTop: 28 }}>
            <div><span className="eyebrow">TRANSACTIONS</span><h2>Payment history</h2></div>
          </div>
          <div className="payments-table" data-testid="user-payments-table">
            <div className="pt-head"><span>Tool</span><span>Amount</span><span>Payment ID</span><span>When</span><span>Status</span></div>
            {payments.map(p => (
              <div className="pt-row user-ptrow" key={p.razorpay_payment_id}>
                <span className="pt-tool"><Tractor size={14} />{p.tool_name}</span>
                <span className="pt-amount">₹{Number(p.amount || 0).toLocaleString()}</span>
                <span className="pt-id" title={p.razorpay_payment_id}>{p.razorpay_payment_id}</span>
                <span>{p.paid_at ? new Date(p.paid_at).toLocaleString() : (p.failed_at ? new Date(p.failed_at).toLocaleString() : "—")}</span>
                <span className={`pt-status ${p.payment_status}`}>{p.payment_status}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </>
  );
}
