import { useEffect, useMemo, useState } from "react";
import { Search, MapPin, Star, Tractor, ChevronRight } from "lucide-react";
import { api } from "../lib/api";
import RentalModal from "../components/RentalModal";
import { toast } from "sonner";

const categories = ["All tools", "Tractors", "Harvesting", "Tillage", "Planting"];

export default function BrowsePage() {
  const [tools, setTools] = useState([]);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("All tools");
  const [onlyAvailable, setOnlyAvailable] = useState(false);
  const [selected, setSelected] = useState(null);

  const load = async () => {
    try { const { data } = await api.get("/tools"); setTools(data); }
    catch { toast.error("Could not load tools"); }
  };
  useEffect(() => { load(); }, []);

  const visible = useMemo(() => tools.filter(t =>
    (category === "All tools" || t.category === category) &&
    (!onlyAvailable || t.available) &&
    `${t.name} ${t.category} ${t.location}`.toLowerCase().includes(query.toLowerCase())
  ), [tools, category, onlyAvailable, query]);

  const requestRental = async (tool, start_date, end_date) => {
    try {
      await api.post("/rentals", { tool_id: tool.id, start_date, end_date });
      toast.success("Rental request sent — waiting for admin approval");
      setSelected(null);
    } catch (e) {
      toast.error(e.response?.data?.detail || "Unable to send request");
    }
  };

  return (
    <>
      <header className="topbar">
        <div>
          <span className="eyebrow">FARMER WORKSPACE</span>
          <h1>Find the right tool for today’s work</h1>
        </div>
        <div className="topbar-meta"><div className="status-dot"></div><span>All systems ready</span></div>
      </header>
      <section className="hero-strip">
        <div>
          <p className="eyebrow light">FIELDWORK, SIMPLIFIED</p>
          <h2>Good tools.<br /><i>Better harvests.</i></h2>
          <p>Rent dependable equipment from trusted local owners, exactly when your fields need it.</p>
        </div>
        <div className="hero-stat"><strong>{tools.length}</strong><span>tools ready<br />to rent</span></div>
      </section>
      <section className="toolbar">
        <div className="search-wrap">
          <Search size={18} />
          <input data-testid="tool-search-input" value={query} onChange={e => setQuery(e.target.value)} placeholder="Search tractors, tillers, harvesters..." />
        </div>
        <div className="filter-row">
          {categories.map(c => (
            <button key={c} className={`filter-pill ${category === c ? "chosen" : ""}`} data-testid={`filter-${c.toLowerCase().replace(" ", "-")}`} onClick={() => setCategory(c)}>{c}</button>
          ))}
          <button className={`availability-toggle ${onlyAvailable ? "on" : ""}`} data-testid="available-only-toggle" onClick={() => setOnlyAvailable(!onlyAvailable)}>
            <span></span>Available now
          </button>
        </div>
      </section>
      <section className="section-head">
        <div>
          <span className="eyebrow">RECOMMENDED FOR YOU</span>
          <h2>Available equipment <small>{visible.length} results</small></h2>
        </div>
      </section>
      <div className="tool-grid">
        {visible.map(tool => (
          <article className="tool-card" key={tool.id} data-testid={`tool-card-${tool.id}`}>
            <div className="tool-image">
              <img src={tool.image_url?.startsWith("/api/") ? `${process.env.REACT_APP_BACKEND_URL}${tool.image_url}` : tool.image_url} alt={tool.name} />
              <span className={tool.available ? "availability available" : "availability"}>{tool.available ? <><span />Available</> : "Booked"}</span>
            </div>
            <div className="tool-info">
              <div className="tool-top">
                <span className="category-tag">{tool.category}</span>
                <span className="rating"><Star size={13} fill="currentColor" />{tool.rating}</span>
              </div>
              <h3>{tool.name}</h3>
              <p className="location"><MapPin size={14} />{tool.location}</p>
              <div className="tool-bottom">
                <div className="price"><strong>₹{tool.daily_rate.toLocaleString()}</strong><span>/ day · ₹{tool.hourly_rate}/hr</span></div>
                <button className="rent-btn" data-testid={`rent-tool-${tool.id}`} disabled={!tool.available} onClick={() => setSelected(tool)}>Rent tool <ChevronRight size={16} /></button>
              </div>
            </div>
          </article>
        ))}
      </div>
      {selected && <RentalModal tool={selected} onClose={() => setSelected(null)} onSubmit={requestRental} />}
    </>
  );
}
