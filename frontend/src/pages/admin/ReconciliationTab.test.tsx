import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import ReconciliationTab from "./ReconciliationTab";
import { api } from "../../lib/api";

vi.mock("../../lib/api", () => ({
  api: { get: vi.fn(), post: vi.fn() },
}));

const discrepancy = {
  user_id: 4,
  account_number: "123456789012",
  expected_balance: "1000.00",
  actual_balance: "1120.50",
  difference: "120.50",
};

function report(id: number, created_at: string) {
  return {
    id,
    status: "discrepancies_found" as const,
    accounts_checked: 40,
    discrepancy_count: 1,
    discrepancies: [discrepancy],
    triggered_by: "scheduled",
    created_at,
  };
}

describe("ReconciliationTab", () => {
  beforeEach(() => {
    vi.mocked(api.get).mockReset();
  });

  it("shows the ledger check once and groups identical earlier runs", async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: [
        report(3, "2026-09-26T08:00:00Z"),
        report(2, "2026-09-26T07:00:00Z"),
        report(1, "2026-09-26T06:00:00Z"),
      ],
    });

    render(<ReconciliationTab />);

    expect(await screen.findByRole("heading", { name: "Current check" })).toBeInTheDocument();
    expect(screen.getAllByText(/wallet is 120.50 ST higher than the ledger/i)).toHaveLength(1);
    expect(screen.getByText("Expected · ledger")).toBeInTheDocument();
    expect(screen.getByText("Actual · wallet")).toBeInTheDocument();
    expect(screen.getByText(/2 runs/)).toBeInTheDocument();
    expect(screen.getByText(/same accounts as the current check/i)).toBeInTheDocument();
  });
});
