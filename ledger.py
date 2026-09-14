import threading
import time
import copy
from typing import Dict, Any, List, Optional

class LedgerEngine:
    def __init__(self):
        self.accounts: Dict[str, float] = {}
        self.processed_events: Dict[str, Dict[str, Any]] = {}
        self.audit_log: List[Dict[str, Any]] = []
        self.fraud_alerts: List[Dict[str, Any]] = []
        self.fraud_rules: List[callable] = []
        self.transactions: Dict[str, List[Any]] = {}  # Added for test_Ledger compatibility
        self._lock = threading.Lock()

    def register_fraud_rule(self, rule_func: callable):
        with self._lock:
            if rule_func not in self.fraud_rules:
                self.fraud_rules.append(rule_func)

    def unregister_fraud_rule(self, rule_func: callable):
        with self._lock:
            if rule_func in self.fraud_rules:
                self.fraud_rules.remove(rule_func)

    def _ensure_account(self, account_id: str):
        if account_id not in self.accounts:
            self.accounts[account_id] = 0.0
        if account_id not in self.transactions:
            self.transactions[account_id] = []

    def ingest(self, event: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            event_id = event.get("event_id")
            account_id = event.get("account_id")
            event_type = event.get("type")
            amount = float(event.get("amount", 0.0))
            target_account_id = event.get("target_account_id")
            original_event_id = event.get("original_event_id")

            if event_id in self.processed_events:
                existing = self.processed_events[event_id]
                if (existing.get("account_id") != account_id or 
                    existing.get("type") != event_type or 
                    existing.get("amount") != amount or
                    existing.get("target_account_id") != target_account_id):
                    return {"status": "CONFLICT", "event_id": event_id, "message": "Event ID reused with conflicting payload."}
                return {"status": "DUPLICATE", "event_id": event_id, "result": existing.get("result")}

            for rule in self.fraud_rules:
                is_fraud, reason = rule(event, self.accounts)
                if is_fraud:
                    alert = {"event_id": event_id, "reason": reason, "timestamp": time.time()}
                    self.fraud_alerts.append(alert)
                    result = {"status": "REJECTED_FRAUD", "reason": reason}
                    self.processed_events[event_id] = {**event, "result": result}
                    return result

            self._ensure_account(account_id)
            result_status = "SUCCESS"
            message = ""

            try:
                if event_type == "DEPOSIT":
                    self.accounts[account_id] += amount
                    self.transactions[account_id].append(event)

                elif event_type == "WITHDRAW":
                    if self.accounts[account_id] < amount:
                        result_status = "FAILED"
                        message = "Insufficient balance."
                    else:
                        self.accounts[account_id] -= amount
                        self.transactions[account_id].append(event)

                elif event_type == "TRANSFER":
                    if not target_account_id:
                        result_status = "FAILED"
                        message = "Target account missing for transfer."
                    elif self.accounts[account_id] < amount:
                        result_status = "FAILED"
                        message = "Insufficient balance for transfer."
                    else:
                        self._ensure_account(target_account_id)
                        self.accounts[account_id] -= amount
                        self.accounts[target_account_id] += amount
                        self.transactions[account_id].append(event)

                elif event_type == "REVERSAL":
                    if not original_event_id:
                        result_status = "FAILED"
                        message = "Original event ID missing for reversal."
                    elif original_event_id not in self.processed_events:
                        result_status = "PENDING_OR_FAILED"
                        message = "Original event not found yet for reversal."
                    else:
                        orig_data = self.processed_events[original_event_id]
                        # Check if already reversed
                        if orig_data.get("reversed", False):
                            result_status = "FAILED"
                            message = "Original event has already been reversed."
                        elif orig_data.get("result", {}).get("status") in ["SUCCESS", "ACCEPTED"]:
                            orig_type = orig_data.get("type")
                            orig_amount = orig_data.get("amount", 0.0)
                            orig_acc = orig_data.get("account_id")
                            orig_target = orig_data.get("target_account_id")

                            if orig_type == "DEPOSIT":
                                self.accounts[orig_acc] -= orig_amount
                            elif orig_type == "WITHDRAW":
                                self.accounts[orig_acc] += orig_amount
                            elif orig_type == "TRANSFER":
                                self.accounts[orig_acc] += orig_amount
                                self.accounts[orig_target] -= orig_amount
                            
                            # Mark original as reversed
                            orig_data["reversed"] = True
                        else:
                            result_status = "FAILED"
                            message = "Original event was not successful, cannot reverse."

                else:
                    result_status = "FAILED"
                    message = f"Unknown event type: {event_type}"

            except Exception as e:
                result_status = "ERROR"
                message = str(e)

            # Map SUCCESS/FAILED to ACCEPTED/REJECTED for test_Ledger compatibility if needed, 
            # or keep standard. Let's make response accept both or map status cleanly.
            response = {"status": result_status, "message": message, "account_balance": self.accounts.get(account_id, 0.0)}
            self.processed_events[event_id] = {**event, "result": response}
            self.audit_log.append({"event_id": event_id, "type": event_type, "status": result_status, "timestamp": time.time()})
            return response

    def get_balance(self, account_id: str) -> float:
        with self._lock:
            return self.accounts.get(account_id, 0.0)

    def create_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "accounts": copy.deepcopy(self.accounts),
                "processed_events": copy.deepcopy(self.processed_events),
                "audit_log": copy.deepcopy(self.audit_log),
                "transactions": copy.deepcopy(self.transactions)
            }

    def snapshot(self) -> Dict[str, Any]:
        """Alias for test_Ledger compatibility"""
        return self.create_snapshot()

    def restore_snapshot(self, snapshot: Dict[str, Any]):
        with self._lock:
            if not isinstance(snapshot, dict) or "accounts" not in snapshot or "processed_events" not in snapshot:
                raise ValueError("Corrupted or truncated snapshot structure.")
            self.accounts = copy.deepcopy(snapshot["accounts"])
            self.processed_events = copy.deepcopy(snapshot["processed_events"])
            self.audit_log = copy.deepcopy(snapshot.get("audit_log", []))
            self.transactions = copy.deepcopy(snapshot.get("transactions", {}))

    def restore(self, snapshot: Dict[str, Any]):
        """Alias for test_Ledger compatibility"""
        self.restore_snapshot(snapshot)