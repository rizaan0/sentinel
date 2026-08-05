export interface RecipientResult {
  account_number: string;
  full_name: string;
}

export interface TransactionReceipt {
  transaction_id: string;
  sender_account_number: string;
  sender_name: string;
  receiver_account_number: string;
  receiver_name: string;
  amount: string;
  remark: string | null;
  status: "completed" | "failed";
  created_at: string;
  direction: "sent" | "received";
  balance_after: string;
}

export interface TransactionSummary {
  transaction_id: string;
  counterparty_account_number: string;
  counterparty_name: string;
  amount: string;
  remark: string | null;
  status: "completed" | "failed";
  created_at: string;
  direction: "sent" | "received";
}

export interface PaginatedTransactions {
  items: TransactionSummary[];
  total: number;
  limit: number;
  offset: number;
}
