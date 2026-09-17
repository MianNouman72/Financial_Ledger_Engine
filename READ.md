# Financial Ledger Engine (Enterprise-Grade)

An ACID-compliant, high-integrity financial ledger engine engineered to handle strict accounting invariants, high concurrency, idempotency, structured error handling, and audit-level compliance.

---

## 🏗️ Architecture Overview
The system follows a clean modular structure separating API routing, core ledger logic, and data validation:
* **API Layer (`api.py`, `main.py`)**: FastAPI endpoints with explicit HTTP status codes, structured response schemas, and custom global exception handling.
* **Ledger Engine (`ledger.py`)**: Core processor handling strict single/double-entry rules, atomic modifications, and historical event tracking.
* **Validation & Models (`models.py`)**: Pydantic-driven request contracts guarding against invalid amounts, negative balances, and malformed identifiers.

---

## 💾 Database & Storage Design
* **In-Memory State with Snapshots**: The core engine maintains thread-safe in-memory dictionaries for accounts (`balances`, `transactions`) and idempotency tracking (`processed_events`).
* **Persistence & Recovery**: Built-in `/snapshot` and `/restore` mechanisms allow continuous state serialization, enabling seamless backup, zero-downtime recovery, and external cold storage sync.

---

## 🔒 Transaction & Consistency Model
* **Accounting Invariants**: Protects against unauthorized overdrafts, invalid withdrawals, and balance mismatches during transfers.
* **Atomic Execution**: Operations either fully commit across source and destination accounts or safely abort without leaving orphan records.
* **Reversal Semantics**: Safe transactional reversals mapped directly back to verified historical `event_id` keys.

---

## ⚡ Concurrency Strategy
* Implements thread-level synchronization via `threading.Lock()` to serialize concurrent execution streams targeting shared account states.
* Completely mitigates race conditions during high-volume simultaneous thread executions.

---

## 🛡️ Idempotency & Error-Handling Strategy
* **Idempotency Keys**: Unique `event_id` checks prevent duplicate request processing caused by network retries.
* **Safe Error Propagation**: Global exception catchers intercept raw stack traces, returning sanitized, structured JSON error payloads (`400`, `422`, `409`) to clients.

---

## 🧪 Testing & Verification
The engine includes a robust test suite covering unit logic, integration boundaries, and adversarial concurrency scenarios.

To run the test suite locally:
```bash
pytest -v