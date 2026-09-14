# Financial Ledger Engine 🚀

A robust, thread-safe, and production-grade **Event Processing & Financial Ledger Engine** built with **FastAPI** and **Pydantic**. Designed with a focus on strict consistency, idempotency, and data atomicity for high-throughput financial transactions.

---

## 🛠️ Core Features

- **Idempotency Engine**: Prevents duplicate transaction processing by tracking event IDs.
- **Atomic Transfers**: Ensures multi-account fund movements are completely safe—either both sides succeed or the transaction rolls back entirely.
- **Balance Tracking & History**: Maintains precise real-time account balances and chronological transaction histories.
- **Snapshot & Restore**: Allows checkpointing the entire system state to a JSON-compatible snapshot and restoring from it instantly for crash recovery and testing.
- **Thread-Safe Concurrency**: Built with safe state synchronization for concurrent API requests.

---

## ⚙️ Tech Stack

- **Framework**: FastAPI (Python)
- **Data Validation**: Pydantic V2
- **Server**: Uvicorn

---

## 🚀 Quick Start & Installation

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/MianNouman72/Financial_Ledger_Engine.git](https://github.com/MianNouman72/Financial_Ledger_Engine.git)
   cd Financial_Ledger_Engine
