from datetime import datetime, timezone, timedelta
from fraud import FraudDetector

class LedgerEngine:
    def __init__(self, allowed_lateness_minutes: int = 5):
        self.accounts: dict[str, float] = {}
        self.transactions: dict[str, list] = {}
        self.processed_events: set[str] = set()
        self.event_payloads: dict[str, dict] = {}
        self.audit_log: list[dict] = []
        self.fraud_alerts: list[dict] = []
        self.allowed_lateness = timedelta(minutes=allowed_lateness_minutes)
        self.fraud_detector = FraudDetector()

    def log_audit(self, event_id: str, status: str, reason: str = None) -> None:
        log_entry = {"event_id": event_id, "status": status}
        if reason:
            log_entry["reason"] = reason
        self.audit_log.append(log_entry)

    def ingest(self, event: dict) -> dict:
        event_id = event.get("event_id")
        account_id = event.get("account_id")
        event_type = event.get("type")
        amount = event.get("amount", 0.0)
        timestamp_str = event.get("timestamp")
        target_account_id = event.get("target_account_id")

        if event_id in self.processed_events:
            if self.event_payloads.get(event_id) != event:
                self.log_audit(event_id, "CONFLICT", "Event ID already exists with different payload.")
                return {"status": "CONFLICT", "message": "Conflict: Event ID reused with different payload."}
            
            self.log_audit(event_id, "DUPLICATE")
            return {"status": "DUPLICATE", "message": "Event already processed."}

        try:
            event_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            current_time = datetime.now(timezone.utc)
            
            if current_time - event_time > self.allowed_lateness:
                self.log_audit(event_id, "REJECTED", "Event arrived outside allowed lateness window.")
                return {"status": "REJECTED", "message": "Late event rejected."}
        except Exception:
            self.log_audit(event_id, "REJECTED", "Invalid timestamp format.")
            return {"status": "REJECTED", "message": "Invalid timestamp format."}

        if account_id and account_id not in self.accounts:
            self.accounts[account_id] = 0.0
            self.transactions[account_id] = []

        # Fraud Detection Check
        history = self.transactions.get(account_id, [])
        if self.fraud_detector.evaluate(event, history):
            self.fraud_alerts.append({"event_id": event_id, "account_id": account_id, "event": event})
            self.log_audit(event_id, "FRAUD_DETECTED", "Triggered pluggable fraud rule.")
            return {"status": "FRAUD_DETECTED", "message": "Transaction flagged by fraud detection rules."}

        # Execution logic
        if event_type == "DEPOSIT":
            self.accounts[account_id] += amount
            self._save_success_event(event_id, event, account_id)
            return {"status": "ACCEPTED"}

        elif event_type == "WITHDRAW":
            if self.accounts[account_id] < amount:
                self.log_audit(event_id, "REJECTED", "Insufficient balance.")
                return {"status": "REJECTED", "message": "Insufficient balance."}
            
            self.accounts[account_id] -= amount
            self._save_success_event(event_id, event, account_id)
            return {"status": "ACCEPTED"}

        elif event_type == "TRANSFER":
            if not target_account_id:
                self.log_audit(event_id, "REJECTED", "Missing target account for transfer.")
                return {"status": "REJECTED", "message": "Missing target account."}

            if self.accounts[account_id] < amount:
                self.log_audit(event_id, "REJECTED", "Insufficient balance for transfer.")
                return {"status": "REJECTED", "message": "Insufficient balance."}

            if target_account_id not in self.accounts:
                self.accounts[target_account_id] = 0.0
                self.transactions[target_account_id] = []

            self.accounts[account_id] -= amount
            self.accounts[target_account_id] += amount

            self._save_success_event(event_id, event, account_id)
            self.transactions[target_account_id].append(event)
            return {"status": "ACCEPTED"}

        elif event_type == "REVERSAL":
            self._save_success_event(event_id, event, account_id)
            return {"status": "ACCEPTED"}

        else:
            self.log_audit(event_id, "REJECTED", "Unknown event type.")
            return {"status": "REJECTED", "message": "Unknown event type."}

    def _save_success_event(self, event_id: str, event: dict, account_id: str) -> None:
        self.processed_events.add(event_id)
        self.event_payloads[event_id] = event
        self.transactions[account_id].append(event)
        self.log_audit(event_id, "ACCEPTED")

    def get_balance(self, account_id: str) -> float:
        return self.accounts.get(account_id, 0.0)

    def get_transactions(self, account_id: str) -> list:
        return self.transactions.get(account_id, [])

    def snapshot(self) -> dict:
        return {
            "accounts": self.accounts,
            "processed_events": list(self.processed_events),
            "audit_log": self.audit_log,
            "fraud_alerts": self.fraud_alerts
        }

    def restore(self, snapshot_data: dict) -> None:
        self.accounts = snapshot_data.get("accounts", {})
        self.processed_events = set(snapshot_data.get("processed_events", []))
        self.audit_log = snapshot_data.get("audit_log", [])
        self.fraud_alerts = snapshot_data.get("fraud_alerts", [])