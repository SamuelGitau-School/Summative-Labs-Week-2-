import { request } from "./client.js";

export const listProducts = () => request("/inventory");
export const createProduct = (data) => request("/inventory", { method: "POST", body: data });
export const updateProduct = (id, data) => request(`/inventory/${id}`, { method: "PATCH", body: data });
export const deleteProduct = (id) => request(`/inventory/${id}`, { method: "DELETE" });
// Fetches details from Open Food Facts and saves them on the item
export const enrichProduct = (id) => request(`/inventory/${id}/enrich`, { method: "POST", body: {} });
