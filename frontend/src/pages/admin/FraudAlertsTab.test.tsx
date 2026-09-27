import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import FraudAlertsTab from "./FraudAlertsTab";
import { api } from "../../lib/api";

vi.mock("../../lib/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
  },
}));

const FAKE_ALERT = {
  id: 1,
  transaction_id: 42,
  user_id: 7,
  account_number: "123456789012",
  transaction_public_id: "tx-abc",
  risk_score: 30,
  triggered_rules: [
    {
      rule_name: "rapid_repeated_transfers",
      explanation: "3 transfers within 60 seconds.",
      risk_weight: 30,
    },
  ],
  status: "open",
  created_at: new Date().toISOString(),
};

describe("FraudAlertsTab (admin alert review)", () => {
  beforeEach(() => {
    vi.mocked(api.get).mockReset();
    vi.mocked(api.patch).mockReset();
  });

  it("renders alerts and allows an admin to change investigation status", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: [FAKE_ALERT] });
    vi.mocked(api.patch).mockResolvedValueOnce({
      data: { ...FAKE_ALERT, status: "investigating" },
    });

    const user = userEvent.setup();
    render(<FraudAlertsTab />);

    expect(await screen.findByText("1234 5678 9012")).toBeInTheDocument();
    expect(screen.getByText("Rapid repeated transfers")).toBeInTheDocument();
    expect(screen.getByText(/risk 30/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /investigate/i }));
    expect(await screen.findByText(/3 transfers within 60 seconds/i)).toBeInTheDocument();

    await user.selectOptions(screen.getByDisplayValue("open"), "investigating");

    expect(api.patch).toHaveBeenCalledWith("/fraud-alerts/1/status", {
      status: "investigating",
    });
  });
});
