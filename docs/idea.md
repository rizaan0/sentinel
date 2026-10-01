# Sentinel — Idea

## The Problem

Digital wallets record a payment and treat it as correct. When something is wrong — a burst of new counterparties, money that arrives and leaves again, a balance that no longer matches its ledger — the check usually happens later, by hand.

Existing approaches fall short in three ways:

1. **Processing and monitoring are separate.** A transfer is committed first. Fraud review, if it happens at all, looks at a payment that has already moved.
2. **Detection and explanation are separate.** A score without the rules that produced it still leaves an analyst to reconstruct the case from raw rows.
3. **The ledger is assumed, not checked.** Wallet balances and double-entry lines can drift, and nothing in the payment path compares them.

## The Opportunity

Sentinel is a peer-to-peer wallet in a dummy currency (ST Coins) with the monitor built into the transfer. Before the ledger changes, completed history is scored. A normal payment commits. A high score asks the sender for a one-time code. A critical score does not complete the transfer and leaves the case with an administrator. After a payment commits, the same ledger can be reconciled, and an administrator can ask a local assistant to explain the stored case.

## Core Value Proposition

- **Score before commit** — the ledger changes only when the action is allow, monitor, or a verified high-risk code
- **Behaviour, not a hand-applied label** — twelve versioned rules, plus an optional Isolation Forest, read completed history
- **Two different high-risk outcomes** — a one-time code for a high score; an uncompleted transfer and an administrator alert for a critical score
- **Ledger check independent of the score** — reconciliation compares each wallet with the sum of its debit and credit lines
- **Explanation without a verdict** — the investigation assistant answers from stored rows and cannot change an alert status

## Target User

Students and operators of a classroom payment system: people who send and receive ST Coins, and administrators who review alerts, reconciliation, and forecasts. It is not a bank and it does not move real money.

## What a person can do

**Sender**

1. Sign up. The account receives a 12-digit account number and an opening balance.
2. Set a transaction PIN. The app requires a PIN before Home, Send, Activity, or Profile.
3. Send ST Coins to another account number. The PIN is checked on the server.
4. If the score is high, read a one-time code in a temporary notice and type it into an empty field. The code is not printed inside the form.
5. If the score is critical, see that the transfer was not completed. Home does not show a held-amount card or an “explain this activity” form.
6. Dismiss an early inbound notice when several similar payments arrive. The notice does not block receiving and does not create a fraud alert.

**Administrator**

1. Watch a live feed of transfers and alerts.
2. Open a fraud alert, read the contributing rules, and confirm or reject it. Confirming fraud can quarantine funds and restrict outgoing payments. Rejecting a case can release a monitoring hold.
3. Run reconciliation and read any account whose wallet does not match its ledger.
4. Read a 7-day risk forecast. The forecast is not a fraud verdict.
5. Ask the investigation assistant about a stored case.
6. Mark a repeated group of inbound payments as legitimate so the same early warning is not shown again.
