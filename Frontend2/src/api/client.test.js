import { vi } from "vitest";
import { request, setUnauthorizedHandler } from "./client.js";

const reply = (status, body) =>
  Promise.resolve({ ok: status < 400, status, json: () => (body === undefined ? Promise.reject(new Error("no body")) : Promise.resolve(body)) });

let onUnauthorized;

beforeEach(() => {
  onUnauthorized = vi.fn();
  setUnauthorizedHandler(onUnauthorized);
  vi.stubGlobal("fetch", vi.fn());
});
afterEach(() => vi.unstubAllGlobals());

describe("request", () => {
  it("returns the parsed JSON on success", async () => {
    fetch.mockReturnValue(reply(200, [{ id: 1 }]));
    expect(await request("/inventory")).toEqual([{ id: 1 }]);
  });

  it("sends a JSON body with the right header", async () => {
    fetch.mockReturnValue(reply(201, { id: 2 }));
    await request("/inventory", { method: "POST", body: { name: "Mug" } });
    const [url, options] = fetch.mock.calls[0];
    expect(url).toBe("/inventory");
    expect(options.method).toBe("POST");
    expect(options.headers).toEqual({ "Content-Type": "application/json" });
    expect(options.body).toBe(JSON.stringify({ name: "Mug" }));
  });

  it("returns null for 204 No Content", async () => {
    fetch.mockReturnValue(reply(204));
    expect(await request("/inventory/1", { method: "DELETE" })).toBeNull();
  });

  it("throws the server's error message", async () => {
    fetch.mockReturnValue(reply(400, { error: "name is required." }));
    await expect(request("/inventory", { method: "POST", body: {} })).rejects.toThrow("name is required.");
  });

  it("explains when the network call itself fails", async () => {
    fetch.mockRejectedValue(new TypeError("Failed to fetch"));
    await expect(request("/inventory")).rejects.toThrow(/Can't reach the server/);
  });

  it("explains a 5xx with no body (Flask is down behind the proxy)", async () => {
    fetch.mockReturnValue(reply(500));
    await expect(request("/inventory")).rejects.toThrow(/Can't reach the server/);
  });

  it("falls back to a generic message for other bodiless errors", async () => {
    fetch.mockReturnValue(reply(418));
    await expect(request("/inventory")).rejects.toThrow("Request failed (418)");
  });

  it("calls the unauthorized handler on a 401 from a data route", async () => {
    fetch.mockReturnValue(reply(401, { error: "Please sign in." }));
    await expect(request("/inventory")).rejects.toThrow("Please sign in.");
    expect(onUnauthorized).toHaveBeenCalledTimes(1);
  });

  it("does not treat a 401 from /auth/ routes as an expired session", async () => {
    fetch.mockReturnValue(reply(401, { error: "Wrong email or password." }));
    await expect(request("/auth/login", { method: "POST", body: {} })).rejects.toThrow("Wrong email or password.");
    expect(onUnauthorized).not.toHaveBeenCalled();
  });
});
