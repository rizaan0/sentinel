import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SendMoneyPage from "./SendMoneyPage";
import { renderWithProviders } from "../../test/testUtils";
import { api } from "../../lib/api";

vi.mock("../../lib/api", () => ({
  api: {
    post: vi.fn(),
    get: vi.fn(),
    defaults: { headers: { common: {} } },
  },
}));

describe("SendMoneyPage", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.mocked(api.post).mockReset();
    vi.mocked(api.get).mockReset();
  });

  it("walks through search -> amount -> review -> authorize -> receipt", async () => {
    vi.mocked(api.get).mockResolvedValueOnce({
      data: { account_number: "999999999999", full_name: "Bob" },
    });
    vi.mocked(api.post).mockResolvedValueOnce({
      data: {
        transaction_id: "tx-123",
        sender_account_number: "111111111111",
        sender_name: "Alice",
        receiver_account_number: "999999999999",
        receiver_name: "Bob",
        amount: "50.00",
        remark: null,
        status: "completed",
        created_at: new Date().toISOString(),
        direction: "sent",
        balance_after: "950.00",
      },
    });

    const user = userEvent.setup();
    renderWithProviders(<SendMoneyPage />);

    // Step 1: search
    await user.type(
      screen.getByLabelText(/recipient account number/i),
      "999999999999",
    );
    await user.click(screen.getByRole("button", { name: /find recipient/i }));

    expect(await screen.findByText("Bob")).toBeInTheDocument();

    // Step 2: amount
    await user.type(screen.getByLabelText(/amount \(st\)/i), "50");
    await user.click(screen.getByRole("button", { name: /review transfer/i }));

    // Step 3: review + PIN authorization
    expect(await screen.findByText(/50 st/i)).toBeInTheDocument();
    await user.type(screen.getByLabelText(/enter transaction pin/i), "1111");
    await user.click(screen.getByRole("button", { name: /authorize transfer/i }));

    // Step 4: receipt
    expect(await screen.findByText(/transfer successful/i)).toBeInTheDocument();
    expect(screen.getByText("tx-123")).toBeInTheDocument();

    expect(api.post).toHaveBeenCalledWith("/transactions/transfer", {
      recipient_account_number: "999999999999",
      amount: "50",
      remark: null,
      pin: "1111",
    });
  });

  it("shows an error when the recipient cannot be found", async () => {
    vi.mocked(api.get).mockRejectedValueOnce({
      response: { data: { detail: "No account found with that number" } },
    });

    const user = userEvent.setup();
    renderWithProviders(<SendMoneyPage />);

    await user.type(screen.getByLabelText(/recipient account number/i), "000000000000");
    await user.click(screen.getByRole("button", { name: /find recipient/i }));

    expect(await screen.findByText(/no account found with that number/i)).toBeInTheDocument();
  });
});
