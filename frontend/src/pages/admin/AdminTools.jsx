import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { Plus, Save, Trash2, Upload, X, Pencil, Search } from "lucide-react";
import { toast } from "sonner";

const empty = { name: "", category: "Tractors", description: "", location: "", owner: "AgriRent Fleet", hourly_rate: 0, daily_rate: 0, available: true, image_url: "", rating: 4.7 };

export default function AdminTools() {
  const [tools, setTools] = useState([]);
  const [editing, setEditing] = useState(null);
  const [q, setQ] = useState("");

  const load = async () => { const { data } = await api.get("/admin/tools"); setTools(data); };
  useEffect(() => { load(); }, []);

  const save = async () => {
    try {
      if (!editing.name || !editing.location || !editing.daily_rate) { toast.error("Name, location and daily rate are required"); return; }
      if (editing.id) {
        await api.patch(`/admin/tools/${editing.id}`, editing);
        toast.success("Tool updated");
      } else {
        await api.post("/admin/tools", editing);
        toast.success("Tool created");
      }
      setEditing(null);
      load();
    } catch (e) { toast.error(e.response?.data?.detail || "Save failed"); }
  };

  const del = async (id) => {
    if (!window.confirm("Delete this tool? This cannot be undone.")) return;
    try { await api.delete(`/admin/tools/${id}`); toast.success("Tool deleted"); load(); }
    catch (e) { toast.error(e.response?.data?.detail || "Delete failed"); }
  };

  const uploadImage = async (id, file) => {
    const form = new FormData();
    form.append("file", file);
    try {
      const { data } = await api.post(`/admin/tools/${id}/image`, form, { headers: { "Content-Type": "multipart/form-data" } });
      toast.success("Image uploaded");
      if (editing && editing.id === id) setEditing({ ...editing, image_url: data.image_url });
      load();
    } catch (e) { toast.error(e.response?.data?.detail || "Upload failed"); }
  };

  const filtered = tools.filter(t => `${t.name} ${t.category} ${t.location}`.toLowerCase().includes(q.toLowerCase()));

  return (
    <>
      <header className="topbar">
        <div>
          <span className="eyebrow">ADMIN CONSOLE</span>
          <h1>Tools</h1>
        </div>
        <div className="topbar-actions">
          <div className="search-wrap admin"><Search size={16} /><input data-testid="admin-tools-search" value={q} onChange={e => setQ(e.target.value)} placeholder="Search tools" /></div>
          <button className="rent-btn" data-testid="admin-add-tool-btn" onClick={() => setEditing({ ...empty })}><Plus size={16} /> Add tool</button>
        </div>
      </header>

      <div className="admin-table" data-testid="admin-tools-table">
        <div className="at-head"><span>Tool</span><span>Category</span><span>Location</span><span>Daily rate</span><span>Available</span><span>Actions</span></div>
        {filtered.map(t => (
          <div className="at-row" key={t.id} data-testid={`admin-tool-row-${t.id}`}>
            <span className="at-name"><img alt="" src={t.image_url?.startsWith("/api/") ? `${process.env.REACT_APP_BACKEND_URL}${t.image_url}` : t.image_url} />{t.name}</span>
            <span>{t.category}</span>
            <span>{t.location}</span>
            <span>₹{Number(t.daily_rate).toLocaleString()}</span>
            <span className={t.available ? "yes" : "no"}>{t.available ? "Yes" : "No"}</span>
            <span className="at-actions">
              <button className="icon-btn" data-testid={`admin-edit-tool-${t.id}`} onClick={() => setEditing({ ...t })} title="Edit"><Pencil size={14} /></button>
              <button className="icon-btn danger" data-testid={`admin-delete-tool-${t.id}`} onClick={() => del(t.id)} title="Delete"><Trash2 size={14} /></button>
            </span>
          </div>
        ))}
      </div>

      {editing && (
        <div className="modal-backdrop" data-testid="admin-tool-modal">
          <div className="modal admin-modal">
            <button className="modal-close icon-btn" onClick={() => setEditing(null)}><X size={18} /></button>
            <span className="eyebrow">{editing.id ? "EDIT TOOL" : "NEW TOOL"}</span>
            <h2>{editing.name || "Untitled tool"}</h2>
            <div className="admin-form">
              <label>Name<input data-testid="tool-form-name" value={editing.name} onChange={e => setEditing({ ...editing, name: e.target.value })} /></label>
              <label>Category<select data-testid="tool-form-category" value={editing.category} onChange={e => setEditing({ ...editing, category: e.target.value })}>{["Tractors", "Harvesting", "Tillage", "Planting", "Irrigation", "Other"].map(c => <option key={c}>{c}</option>)}</select></label>
              <label>Location<input data-testid="tool-form-location" value={editing.location} onChange={e => setEditing({ ...editing, location: e.target.value })} /></label>
              <label>Owner<input data-testid="tool-form-owner" value={editing.owner} onChange={e => setEditing({ ...editing, owner: e.target.value })} /></label>
              <label>Hourly rate ₹<input type="number" data-testid="tool-form-hourly" value={editing.hourly_rate} onChange={e => setEditing({ ...editing, hourly_rate: Number(e.target.value) })} /></label>
              <label>Daily rate ₹<input type="number" data-testid="tool-form-daily" value={editing.daily_rate} onChange={e => setEditing({ ...editing, daily_rate: Number(e.target.value) })} /></label>
              <label className="span-2">Description<textarea data-testid="tool-form-description" value={editing.description} onChange={e => setEditing({ ...editing, description: e.target.value })} /></label>
              <label className="checkbox-row"><input type="checkbox" data-testid="tool-form-available" checked={editing.available} onChange={e => setEditing({ ...editing, available: e.target.checked })} /> Available for rent</label>
              <label className="span-2">Image URL<input data-testid="tool-form-image-url" value={editing.image_url} onChange={e => setEditing({ ...editing, image_url: e.target.value })} placeholder="https://... or upload below" /></label>
              {editing.id && (
                <label className="span-2 upload-row">
                  <span>Upload image file</span>
                  <input type="file" accept="image/*" data-testid="tool-form-image-upload" onChange={e => e.target.files?.[0] && uploadImage(editing.id, e.target.files[0])} />
                </label>
              )}
              {editing.image_url && <div className="span-2 preview"><img alt="preview" src={editing.image_url.startsWith("/api/") ? `${process.env.REACT_APP_BACKEND_URL}${editing.image_url}` : editing.image_url} /></div>}
            </div>
            <button className="confirm-btn" data-testid="tool-form-save" onClick={save}><Save size={16} /> {editing.id ? "Save changes" : "Create tool"}</button>
          </div>
        </div>
      )}
    </>
  );
}
