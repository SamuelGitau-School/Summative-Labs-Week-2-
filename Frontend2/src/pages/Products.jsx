import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import {
  listProducts, createProduct, updateProduct, deleteProduct, enrichProduct,
} from "../api/products.js";

const EMPTY = { name: "", category: "", price: "", stock: "", barcode: "" };

export default function Products() {
  const { user, signOut } = useAuth();
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState(EMPTY);
  const [editingId, setEditingId] = useState(null);
  const [errors, setErrors] = useState({});
  const [message, setMessage] = useState(""); // errors from the server
  const [busyId, setBusyId] = useState(null); // row being looked up

  useEffect(() => {
    listProducts()
      .then(setProducts)
      .catch((e) => setMessage(e.message))
      .finally(() => setLoading(false));
  }, []);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const validate = () => {
    const er = {};
    if (!form.name.trim()) er.name = "Name is required.";
    if (!form.category.trim()) er.category = "Category is required.";
    if (form.price === "" || Number(form.price) < 0) er.price = "Enter a price of 0 or more.";
    if (form.stock === "" || !Number.isInteger(Number(form.stock)) || Number(form.stock) < 0)
      er.stock = "Enter a whole number of 0 or more.";
    if (form.barcode.trim() && !/^\d{8,14}$/.test(form.barcode.trim()))
      er.barcode = "Use 8 to 14 digits, or leave blank.";
    setErrors(er);
    return Object.keys(er).length === 0;
  };

  const cancel = () => { setEditingId(null); setForm(EMPTY); setErrors({}); };

  const submit = async (e) => {
    e.preventDefault();
    if (!validate()) return;
    const data = {
      name: form.name.trim(),
      category: form.category.trim(),
      price: Number(form.price),
      stock: Number(form.stock),
    };
    if (form.barcode.trim()) data.barcode = form.barcode.trim(); // optional
    setMessage("");
    try {
      if (editingId) {
        const saved = await updateProduct(editingId, data);
        setProducts((list) => list.map((p) => (p.id === editingId ? saved : p)));
      } else {
        const saved = await createProduct(data);
        setProducts((list) => [...list, saved]);
      }
      cancel();
    } catch (err) {
      setMessage(err.message);
    }
  };

  const edit = (p) => {
    setEditingId(p.id);
    setForm({
      name: p.name, category: p.category,
      price: String(p.price), stock: String(p.stock), barcode: p.barcode ?? "",
    });
    setErrors({});
    setMessage("");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const remove = async (p) => {
    if (!window.confirm(`Delete "${p.name}"?`)) return;
    setMessage("");
    try {
      await deleteProduct(p.id);
      setProducts((list) => list.filter((x) => x.id !== p.id));
      if (editingId === p.id) cancel();
    } catch (err) {
      setMessage(err.message);
    }
  };

  const lookUp = async (p) => {
    setBusyId(p.id);
    setMessage("");
    try {
      const saved = await enrichProduct(p.id);
      setProducts((list) => list.map((x) => (x.id === p.id ? saved : x)));
    } catch (err) {
      setMessage(err.message);
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="wrap">
      <header className="bar">
        <h1>Stockroom</h1>
        <div>
          <span className="who">{user.email}</span>
          <button onClick={signOut}>Sign out</button>
        </div>
      </header>

      {message && <p className="banner" role="alert">{message}</p>}

      <section className="panel">
        <h2>{editingId ? "Edit product" : "Add a product"}</h2>
        <form onSubmit={submit} noValidate className="grid">
          <label>Name
            <input value={form.name} onChange={set("name")} />
            {errors.name && <span className="error">{errors.name}</span>}
          </label>
          <label>Category
            <input value={form.category} onChange={set("category")} />
            {errors.category && <span className="error">{errors.category}</span>}
          </label>
          <label>Price (USD)
            <input type="number" min="0" step="0.01" value={form.price} onChange={set("price")} />
            {errors.price && <span className="error">{errors.price}</span>}
          </label>
          <label>In stock
            <input type="number" min="0" step="1" value={form.stock} onChange={set("stock")} />
            {errors.stock && <span className="error">{errors.stock}</span>}
          </label>
          <label>Barcode (optional)
            <input inputMode="numeric" value={form.barcode} onChange={set("barcode")} />
            {errors.barcode && <span className="error">{errors.barcode}</span>}
          </label>
          <div className="actions">
            <button className="primary" type="submit">{editingId ? "Save changes" : "Add product"}</button>
            {editingId && <button type="button" onClick={cancel}>Cancel</button>}
          </div>
        </form>
      </section>

      <section className="panel">
        <h2>Products ({products.length})</h2>
        {loading ? (
          <p className="empty">Loading products…</p>
        ) : products.length === 0 ? (
          <p className="empty">No products yet. Add your first one above.</p>
        ) : (
          <div className="scroll">
            <table>
              <thead>
                <tr><th>Name</th><th>Category</th><th className="num">Price</th><th className="num">Stock</th><th>Added by</th><th></th></tr>
              </thead>
              <tbody>
                {products.map((p) => {
                  const mine = p.user_id === user.id; // only the person who added an item can change it
                  const lockedTip = mine ? "" : "Only the person who added this can change it";
                  return (
                  <tr key={p.id} className={p.id === editingId ? "editing" : ""}>
                    <td>
                      <div className="name-cell">
                        {p.details?.image_url && <img src={p.details.image_url} alt="" loading="lazy" />}
                        <div>
                          {p.name}
                          {p.details && (
                            <div className="meta">
                              {[p.details.brands, p.details.quantity].filter(Boolean).join(" · ")}
                              {p.details.nutriscore_grade && (
                                <span className="badge">Nutri-Score {p.details.nutriscore_grade.toUpperCase()}</span>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    </td>
                    <td>{p.category}</td>
                    <td className="num">${p.price.toFixed(2)}</td>
                    <td className="num">{p.stock}</td>
                    <td className="owner">{mine ? "You" : p.added_by}</td>
                    <td className="row-actions">
                      <button onClick={() => lookUp(p)} disabled={!mine || busyId === p.id} title={lockedTip}>
                        {busyId === p.id ? "Looking up…" : p.details ? "Refresh info" : "Look up"}
                      </button>
                      <button onClick={() => edit(p)} disabled={!mine} title={lockedTip}>Edit</button>
                      <button className="danger" onClick={() => remove(p)} disabled={!mine} title={lockedTip}>Delete</button>
                    </td>
                  </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
