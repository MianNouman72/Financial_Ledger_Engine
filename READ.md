# Financial Ledger Engine (Enterprise-Grade)

An ACID-compliant, high-integrity financial ledger engine engineered to handle strict accounting invariants, high concurrency, idempotency, and robust error handling.

---

## 🏗️ Architecture Overview
The system follows a clean, modular layered architecture separating API routing, business ledger logic, fraud detection, and validation layers:
* **API Layer (`api.py`, `main.py`)**: FastAPI-powered endpoints with strict Pydantic request/response schemas and global custom exception handling.
* **Ledger Engine (`ledger.py`)**: Core transaction processor implementing atomic balance modifications, thread-level concurrency locking, and immutable audit logs.
* **Fraud Prevention (`fraud.py`)**: Pluggable rule engine intercepting suspicious transactions prior to ledger commitment.

---

## 🔒 Transaction & Consistency Model
* **Atomic Operations**: Financial entries are processed atomically to ensure partial commits never corrupt account balances.
* **Accounting Invariants**: Strict rules prevent invalid withdrawals, negative balances (unless permitted), and malformed transfers.
* **Reversal Semantics**: Built-in support for safe transaction reversals mapped back to original verified event IDs.

---

## ⚡ Concurrency Strategy
* Uses thread-level synchronization (`threading.Lock()`) to serialize concurrent execution streams targeting shared account states.
* Protects against race conditions during high-volume simultaneous deposits, withdrawals, and transfers.

---

## 🛡️ Idempotency & Error Handling
* **Idempotency Keys**: Unique `event_id` tracking prevents duplicate request executions and network retry anomalies.
* **Structured Errors**: Global exception catchers ensure raw stack traces or internal server details are never leaked to clients, returning clean JSON error payloads instead.

---

## 🧪 Testing & Verification
The engine includes a comprehensive test suite covering unit behavior, integration boundaries, and adversarial concurrency cases.

To run the test suite locally:
```bash
pytest -v