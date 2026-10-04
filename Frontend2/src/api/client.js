// Shared fetch wrapper for the Flask API (proxied through Vite, see vite.config.js).
// The browser sends the session cookie automatically because the requests are same-origin.
let onUnauthorized = () => {};
export const setUnauthorizedHandler = (fn) => { onUnauthorized = fn; };

export async function request(path, { method = "GET", body } = {}) {
  let res;
  try {
    res = await fetch(path, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new Error("Can't reach the server. Is the Flask backend running on port 5000?");
  }
  const data = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) {
    // Session expired while using the app: send the user back to sign in
    if (res.status === 401 && !path.startsWith("/auth/")) onUnauthorized();
    // Vite answers 5xx with no JSON body when Flask is down
    const down = res.status >= 500 && !data;
    throw new Error(data?.error || (down
      ? "Can't reach the server. Is the Flask backend running on port 5000?"
      : `Request failed (${res.status})`));
  }
  return data;
}
