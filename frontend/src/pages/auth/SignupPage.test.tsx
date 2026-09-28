import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SignupPage from "./SignupPage";
import { renderWithProviders } from "../../test/testUtils";
import { api } from "../../lib/api";

vi.mock("@/components/motion/shader-background", () => ({
  ShaderBackground: () => null,
}));

vi.mock("../../lib/api", () => ({
  api: {
    post: vi.fn(),
    get: vi.fn(),
    defaults: { headers: { common: {} } },
  },
}));

describe("SignupPage", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.mocked(api.post).mockReset();
    vi.mocked(api.get).mockReset();
  });

  it("submits the form and calls the signup API with the entered values", async () => {
    vi.mocked(api.post).mockResolvedValueOnce({
      data: {
        access_token: "fake-token",
        user: {
          id: 1,
          full_name: "Alice",
          email: "alice@example.com",
          account_number: "123456789012",
          role: "user",
          pin_is_set: false,
          balance: "1000.00",
        },
      },
    });

    const user = userEvent.setup();
    renderWithProviders(<SignupPage />);

    await user.type(screen.getByLabelText(/full name/i), "Alice");
    await user.type(screen.getByLabelText(/^email/i), "alice@example.com");
    await user.type(screen.getByLabelText(/password/i), "supersecret1");
    await user.click(screen.getByRole("button", { name: /sign up/i }));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith("/auth/signup", {
        full_name: "Alice",
        email: "alice@example.com",
        password: "supersecret1",
      });
    });
  });

  it("shows an error message when signup fails", async () => {
    vi.mocked(api.post).mockRejectedValueOnce({
      response: { data: { detail: "Email already registered" } },
    });

    const user = userEvent.setup();
    renderWithProviders(<SignupPage />);

    await user.type(screen.getByLabelText(/full name/i), "Alice");
    await user.type(screen.getByLabelText(/^email/i), "alice@example.com");
    await user.type(screen.getByLabelText(/password/i), "supersecret1");
    await user.click(screen.getByRole("button", { name: /sign up/i }));

    expect(await screen.findByText(/email already registered/i)).toBeInTheDocument();
  });
});
