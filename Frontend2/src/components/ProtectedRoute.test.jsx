import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { vi } from "vitest";

const FUTURE = { v7_startTransition: true, v7_relativeSplatPath: true };
import ProtectedRoute from "./ProtectedRoute.jsx";
import { useAuth } from "../context/AuthContext.jsx";

vi.mock("../context/AuthContext.jsx", () => ({ useAuth: vi.fn() }));

function renderAt(path = "/products") {
  return render(
    <MemoryRouter initialEntries={[path]} future={FUTURE}>
      <Routes>
        <Route path="/signin" element={<p>sign-in page</p>} />
        <Route path="/products" element={<ProtectedRoute><p>secret products</p></ProtectedRoute>} />
      </Routes>
    </MemoryRouter>
  );
}

describe("ProtectedRoute", () => {
  it("shows the page to a signed-in user", () => {
    useAuth.mockReturnValue({ user: { id: 1, email: "a@b.com" }, loading: false });
    renderAt();
    expect(screen.getByText("secret products")).toBeInTheDocument();
  });

  it("redirects a signed-out visitor to /signin", () => {
    useAuth.mockReturnValue({ user: null, loading: false });
    renderAt();
    expect(screen.getByText("sign-in page")).toBeInTheDocument();
    expect(screen.queryByText("secret products")).not.toBeInTheDocument();
  });

  it("waits while the session is being checked instead of redirecting", () => {
    useAuth.mockReturnValue({ user: null, loading: true });
    renderAt();
    expect(screen.getByText(/checking your session/i)).toBeInTheDocument();
    expect(screen.queryByText("sign-in page")).not.toBeInTheDocument();
  });
});
