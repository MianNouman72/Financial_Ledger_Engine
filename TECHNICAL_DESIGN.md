# Technical Design Document: Adversarial Financial Ledger Engine

## 1. Concurrency Model & Safety
The engine utilizes a re-entrant mutual exclusion lock (`threading.Lock`) embedded inside the `LedgerEngine` class. Every state mutation (ingestion, balance check, snapshot creation, and rule registration) acquires this lock atomically. This prevents race conditions, dirty reads, and torn writes when multiple worker threads or asynchronous API clients submit transactions concurrently.

## 2. Atomicity Guarantees
Atomicity is enforced through strict transaction boundary checks. For multi-account transfers, validation (e.g., checking sufficient balance) and execution (subtracting from source and adding to target) occur within the same locked critical section. If any condition fails (e.g., insufficient balance or missing target account), the transaction aborts with status `FAILED`, leaving account balances completely unmodified (all-or-nothing semantic).

## 3. Deterministic Ordering & Invariants
Deterministic ordering is maintained by processing events sequentially in the exact order they acquire the engine lock. Invariant rules—such as non-negative account balances and money conservation across transfers—are continuously verified across all test permutations and multi-threaded stress runs.

## 4. Idempotency & Conflict Detection
Idempotency is achieved using a persistent `processed_events` dictionary keyed by unique `event_id`s. When an event arrives:
* If the `event_id` exists with an **identical payload**, the engine returns the cached result immediately (`DUPLICATE`).
* If the `event_id` exists with a **differing payload**, the engine flags it as a `CONFLICT`, preventing replay attacks or accidental data corruption.

## 5. Crash Recovery & Failure Semantics
State persistence is supported via deep-copy snapshots (`create_snapshot` and `restore_snapshot`). If a process crash occurs mid-transfer, volatile memory is cleared, but system state can be recovered up to the last valid snapshot checkpoint. Snapshot structures are validated upon restoration to reject corrupted or truncated state payloads.

## 6. Time and Space Complexity
* **Ingestion (`ingest`)**: $O(1)$ average time complexity for lookup and state update using hash maps.
* **Fraud Rule Evaluation**: $O(K)$ where $K$ is the number of active pluggable fraud rules.
* **Space Complexity**: $O(N + E)$ where $N$ is the number of active accounts and $E$ is the total processed events stored for audit and idempotency tracking. Memory is optimized for large-scale NDJSON streaming via line-by-line generators rather than full payload buffering.

## 7. Architectural Maintainability
The architecture decouples core ledger accounting (`ledger.py`), pluggable security policies (`fraud.py`), and transport layers (`main.py`). New event types or custom fraud checks can be injected dynamically via registration hooks without modifying or risking regressions in the core ledger engine.