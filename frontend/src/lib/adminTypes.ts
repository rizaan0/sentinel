export interface PlatformStats {
  total_users: number;
  total_transactions: number;
  total_volume: string;
  open_alerts: number;
  latest_reconciliation_status: string | null;
}

export interface PlatformTransaction {
  transaction_id: string;
  sender_account_number: string;
  sender_name: string;
  receiver_account_number: string;
  receiver_name: string;
  amount: string;
  remark: string | null;
  status: "completed" | "failed";
  created_at: string;
}

export interface TriggeredRule {
  rule_name: string;
  explanation: string;
  risk_weight: number;
}

export type AlertStatus = "open" | "investigating" | "resolved" | "false_positive";

export interface FraudAlert {
  id: number;
  transaction_id: number;
  user_id: number;
  account_number: string;
  transaction_public_id: string;
  risk_score: number;
  triggered_rules: TriggeredRule[];
  status: AlertStatus;
  created_at: string;
}

export interface ReconciliationDiscrepancy {
  user_id: number;
  account_number: string;
  expected_balance: string;
  actual_balance: string;
  difference: string;
}

export type RiskLevel = "low" | "medium" | "high";

export interface RiskPrediction {
  id: number;
  user_id: number;
  account_number: string;
  predicted_risk_level: RiskLevel;
  trend_score: number;
  alerts_last_7d: number;
  alerts_prior_7d: number;
  avg_risk_score_last_7d: number;
  created_at: string;
}

export interface ReconciliationReport {
  id: number;
  status: "clean" | "discrepancies_found";
  accounts_checked: number;
  discrepancy_count: number;
  discrepancies: ReconciliationDiscrepancy[];
  triggered_by: string;
  created_at: string;
}

export interface AssistantLogEntry {
  id: number;
  question: string;
  answer: string;
  transaction_id: number | null;
  target_account_number: string | null;
  created_at: string;
}

export interface LiveFeedEvent {
  type: "transaction" | "fraud_alert";
  payload: Record<string, unknown>;
  receivedAt: string;
}
