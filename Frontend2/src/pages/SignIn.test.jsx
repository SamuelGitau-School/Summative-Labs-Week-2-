import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

const FUTURE = { v7_startTransition: true, v7_relativeSplatPath: true };
import SignIn, { DEMO } from "./SignIn.jsx";
import { useAuth } from "../context/AuthContext.jsx";

vi.mock("../context/AuthContext.jsx", () => ({ useAuth: vi.fn() }));

const signIn = vi.fn();
const register = vi.fn();

function renderPage() {
  return render(<MemoryRouter future={FUTURE}><SignIn /></MemoryRouter>);
}

const field = (label) => screen.getByLabelText(label);

beforeEach(() => {
  signIn.mockReset().mockResolvedValue();
  register.mockReset().mockResolvedValue();
  useAuth.mockReturnValue({ user: null, loading: false, signIn, register });
});

describe("sign in", () => {
  it("has no confirm-password field", () => {
    renderPage();
    expect(screen.queryByLabelText(/confirm password/i)).not.toBeInTheDocument();
  });

  it("validates the email and password before calling the server", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.type(field("Email"), "nope");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Enter a valid email address.");

    await user.clear(field("Email"));
    await user.type(field("Email"), "a@b.com");
    await user.type(field("Password"), "123");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(screen.getByRole("alert")).toHaveTextContent("at least 6 characters");
    expect(signIn).not.toHaveBeenCalled();
  });

  it("calls signIn with the typed credentials", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.type(field("Email"), "a@b.com");
    await user.type(field("Password"), "secret12");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(signIn).toHaveBeenCalledWith("a@b.com", "secret12");
  });

  it("shows the server's error message", async () => {
    signIn.mockRejectedValue(new Error("Wrong email or password."));
    const user = userEvent.setup();
    renderPage();
    await user.type(field("Email"), "a@b.com");
    await user.type(field("Password"), "secret12");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Wrong email or password.");
    expect(screen.getByRole("button", { name: "Sign in" })).toBeEnabled(); // can retry
  });

  it("the demo button signs in with the demo account", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByRole("button", { name: /try the demo account/i }));
    expect(signIn).toHaveBeenCalledWith(DEMO.email, DEMO.password);
  });
});

describe("register", () => {
  async function openRegister(user) {
    renderPage();
    await user.click(screen.getByRole("button", { name: "Create an account" }));
  }

  it("shows a confirm-password field", async () => {
    await openRegister(userEvent.setup());
    expect(field("Confirm password")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create account" })).toBeInTheDocument();
  });

  it("blocks mismatched passwords without calling the server", async () => {
    const user = userEvent.setup();
    await openRegister(user);
    await user.type(field("Email"), "a@b.com");
    await user.type(field("Password"), "secret12");
    await user.type(field("Confirm password"), "different1");
    await user.click(screen.getByRole("button", { name: "Create account" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Passwords do not match.");
    expect(register).not.toHaveBeenCalled();
  });

  it("blocks an empty confirmation", async () => {
    const user = userEvent.setup();
    await openRegister(user);
    await user.type(field("Email"), "a@b.com");
    await user.type(field("Password"), "secret12");
    await user.click(screen.getByRole("button", { name: "Create account" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Passwords do not match.");
    expect(register).not.toHaveBeenCalled();
  });

  it("sends email, password and confirmation when they match", async () => {
    const user = userEvent.setup();
    await openRegister(user);
    await user.type(field("Email"), " a@b.com ");
    await user.type(field("Password"), "secret12");
    await user.type(field("Confirm password"), "secret12");
    await user.click(screen.getByRole("button", { name: "Create account" }));
    expect(register).toHaveBeenCalledWith("a@b.com", "secret12", "secret12");
  });

  it("clears the confirmation and error when switching back to sign in", async () => {
    const user = userEvent.setup();
    await openRegister(user);
    await user.type(field("Email"), "a@b.com");
    await user.type(field("Password"), "secret12");
    await user.type(field("Confirm password"), "x");
    await user.click(screen.getByRole("button", { name: "Create account" }));
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Create an account" }));
    expect(field("Confirm password")).toHaveValue("");
  });

  it("shows the server's error, such as a duplicate email", async () => {
    register.mockRejectedValue(new Error("That email is already registered."));
    const user = userEvent.setup();
    await openRegister(user);
    await user.type(field("Email"), "a@b.com");
    await user.type(field("Password"), "secret12");
    await user.type(field("Confirm password"), "secret12");
    await user.click(screen.getByRole("button", { name: "Create account" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("already registered");
  });
});
