import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PinSetupPage from "./PinSetupPage";
import { renderWithProviders } from "../../test/testUtils";
import { api } from "../../lib/api";

vi.mock("../../lib/api", () => ({
  api: {
    post: vi.fn(),
    get: vi.fn(),
    defaults: { headers: { common: {} } },
  },
}));

describe("PinSetupPage", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.mocked(api.post).mockReset();
    vi.mocked(api.get).mockReset();
  });

  it("rejects mismatched PINs without calling the API", async () => {
    const user = userEvent.setup();
    renderWithProviders(<PinSetupPage />);

    await user.type(screen.getByLabelText(/pin \(4-6 digits\)/i), "1234");
    await user.type(screen.getByLabelText(/confirm pin/i), "5678");
    await user.click(screen.getByRole("button", { name: /set pin/i }));

    expect(await screen.findByText(/pins do not match/i)).toBeInTheDocument();
    expect(api.post).not.toHaveBeenCalled();
  });

  it("submits the PIN when both entries match", async () => {
    vi.mocked(api.post).mockResolvedValueOnce({ data: { pin_is_set: true } });
    vi.mocked(api.get).mockResolvedValueOnce({
      data: {
        id: 1,
        full_name: "Alice",
        email: "alice@example.com",
        account_number: "123456789012",
        role: "user",
        pin_is_set: true,
        balance: "1000.00",
      },
    });

    const user = userEvent.setup();
    renderWithProviders(<PinSetupPage />);

    await user.type(screen.getByLabelText(/pin \(4-6 digits\)/i), "1234");
    await user.type(screen.getByLabelText(/confirm pin/i), "1234");
    await user.click(screen.getByRole("button", { name: /set pin/i }));

    await vi.waitFor(() => {
      expect(api.post).toHaveBeenCalledWith("/pin/setup", { pin: "1234" });
    });
  });
});
