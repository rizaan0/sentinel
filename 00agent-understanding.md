# Agent Understanding of Sentinel

This document records my understanding of the Sentinel project vision so the user can verify it before implementation begins.

---

## What Sentinel Is

Sentinel is a real-time transaction monitoring platform built on virtual currency. It is not a fraud detection tool with a payment simulator bolted on. It is a payment platform first, with an intelligent monitoring layer that observes, analyzes, explains, and predicts operational risk entirely behind the scenes.

---

## The Two Distinct Experiences

### 1. User-Facing Payment Application

- **Landing page**: A professionally designed product website that introduces Sentinel before any login. It showcases features, previews the dashboard, and demonstrates frontend engineering skill.
- **Registration**: Each new user receives a unique account number (the primary identifier for transfers), 1000 ST Coins starting balance, and is required to create a Transaction PIN before first use.
- **Transaction PIN**: Acts as the UPI-equivalent authorization mechanism. Stored hashed, never plain text. Required on every outgoing transfer.
- **Payment interface**: Inspired by GPay/PhonePe. Users view their balance, see recent history, search for recipients by account number, enter an amount and optional remark, review details, authorize with PIN, and receive a receipt with a unique transaction ID.
- **User awareness**: Users never see monitoring, fraud scores, or alerts. They experience only a payment application.

### 2. Monitoring Engine (Invisible to Users)

Every completed transaction automatically enters the Transaction Monitoring Engine, which runs the following pipeline in sequence:

1. Transaction integrity validation
2. Double-entry ledger recording
3. Reconciliation checks (accounting consistency)
4. Rule-based fraud detection
5. ML-based fraud risk scoring
6. Anomaly prediction (future risk estimation)
7. Alert generation for suspicious patterns

Fraud is not manually injected or labeled. It emerges naturally from user behavior. Patterns the engine treats as suspicious include:

- Rapid repeated transfers between the same accounts
- Circular fund flows across multiple accounts
- Unusually large transfers relative to a user's history
- High-velocity small transactions in a short window

These are valid payment transactions. The monitoring engine identifies them as behavioral anomalies.

### 3. Admin Operational Dashboard

Administrators see a completely different environment:

- **Live transaction stream**: All transactions across the platform in real time.
- **Fraud alerts**: Suspicious transactions with risk scores, triggered rules, behavioral explanations, and investigation status.
- **Reconciliation reports**: Ledger inconsistencies, missing entries, accounting mismatches.
- **Predictive analytics**: Future anomaly frequency and risk estimates based on historical patterns.
- **AI Investigation Assistant**: A RAG-based tool that answers natural-language questions about flagged transactions and users. It retrieves transaction history, fraud rules, monitoring logs, and reconciliation results to produce human-readable investigation summaries. It assists investigators rather than replacing their judgment.

---

## Core Identity

The payment interface exists to generate authentic transaction behavior.
The monitoring platform exists to transform that behavior into meaningful operational intelligence.
That distinction defines what Sentinel is.

---

## Tech Stack (as specified)

- **Frontend**: React, TypeScript, Vite, TailwindCSS, React Router, Axios, Socket.IO Client
- **Backend**: FastAPI, SQLAlchemy, PostgreSQL, Redis, WebSockets
- **ML**: Python, Scikit-learn, XGBoost, Pandas, NumPy
- **AI**: RAG pipeline, pgvector (planned), Sentence Transformers

---

## Development Rules I Will Follow

- Business logic stays in backend services. Frontend components contain no business logic.
- Do not introduce new frameworks, redesign the architecture, or replace technologies without approval.
- Follow existing project conventions. Keep commits focused on a single feature.
- Read the latest specification before implementing any feature.
- Ask for clarification instead of making assumptions when requirements are ambiguous.
- Financial records must never be silently modified. Fail loudly instead of hiding errors.
