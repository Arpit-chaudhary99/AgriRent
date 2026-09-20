import { useMemo, useState } from "react";
import { MapPin, X, ChevronRight, CalendarDays } from "lucide-react";

export default function RentalModal({ tool, onClose, onSubmit }) {
  const today = new Date().toISOString().slice(0, 10);
  const [startDate, setStartDate] = useState(today);
  const [endDate, setEndDate] = useState(today);

  const days = useMemo(() => {
    const s = new Date(startDate); const e = new Date(endDate);
    if (isNaN(s) || isNaN(e) || e < s) return 0;
    return Math.max(1, Math.round((e - s) / (24 * 3600 * 1000)) + 1);
  }, [startDate, endDate]);
  const total = days * tool.daily_rate;

  return (
    <div className="modal-backdrop" data-testid="rental-modal">
      <div className="modal">
        <button className="modal-close icon-btn" data-testid="close-rental-modal" onClick={onClose}><X size={18} /></button>
        <span className="eyebrow">RENTAL REQUEST</span>
        <h2>{tool.name}</h2>
        <p className="modal-location"><MapPin size={14} />{tool.location} · {tool.owner}</p>
        <div className="modal-rule" />
        <label className="date-row">
          <span><CalendarDays size={14} /> Start date</span>
          <input type="date" data-testid="rental-start-date" min={today} value={startDate} onChange={e => { setStartDate(e.target.value); if (endDate < e.target.value) setEndDate(e.target.value); }} />
        </label>
        <label className="date-row">
          <span><CalendarDays size={14} /> End date</span>
          <input type="date" data-testid="rental-end-date" min={startDate} value={endDate} onChange={e => setEndDate(e.target.value)} />
        </label>
        <div className="total-line">
          <span>{days} day{days !== 1 ? "s" : ""} · ₹{tool.daily_rate.toLocaleString()}/day</span>
          <strong>₹{total.toLocaleString()}</strong>
        </div>
        <button className="confirm-btn" data-testid="confirm-rental-button" disabled={days < 1} onClick={() => onSubmit(tool, startDate, endDate)}>
          Send rental request <ChevronRight size={17} />
        </button>
        <p className="modal-note">The admin will confirm availability shortly.</p>
      </div>
    </div>
  );
}
