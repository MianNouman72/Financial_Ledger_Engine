from collections import defaultdict
from datetime import datetime
import threading
from typing import Dict, List, Optional
from models import AuditLogEntry, AuditStatus, Event, EventType

class LedgerEngine:
    def __init__(self, allowed_lateness_seconds: int = 300):
        self.balances: Dict[str, float] = defaultdict(float)
        self.transactions: Dict[str, List[Event]] = defaultdict(list)
        self.processed_events: Dict[str, Event] = {}
        self.audit_log: List[AuditLogEntry] = []
        self._lock = threading.Lock()
        self.allowed_lateness_seconds = allowed_lateness_seconds

    def get_balance(self, account_id: str) -> float:
        with self._lock:
            return self.balances[account_id]

    def get_transactions(self, account_id: str) -> List[Event]:
        with self._lock:
            return list(self.transactions[account_id])

    def ingest(self, event: Event) -> AuditLogEntry:
        with self._lock:
            if event.event_id in self.processed_events:
                existing_event = self.processed_events[event.event_id]
                if existing_event != event:
                    entry = AuditLogEntry(
                        event_id=event.event_id,
                        status=AuditStatus.CONFLICT,
                        reason="Event ID already exists with different payload"
                    )
                    self.audit_log.append(entry)
                    return entry
                else:
                    entry = AuditLogEntry(
                        event_id=event.event_id,
                        status=AuditStatus.DUPLICATE,
                        reason="Duplicate event ignored"
                    )
                    self.audit_log.append(entry)
                    return entry

            try:
                if event.type == EventType.DEPOSIT:
                    self.balances[event.account_id] += event.amount
                
                elif event.type == EventType.WITHDRAW or event.type == EventType.FEE:
                    if self.balances[event.account_id] < event.amount:
                        entry = AuditLogEntry(
                            event_id=event.event_id,
                            status=AuditStatus.REJECTED,
                            reason="Insufficient balance"
                        )
                        self.audit_log.append(entry)
                        return entry
                    self.balances[event.account_id] -= event.amount
                
                elif event.type == EventType.TRANSFER:
                    if not event.target_account_id:
                        entry = AuditLogEntry(
                            event_id=event.event_id,
                            status=AuditStatus.REJECTED,
                            reason="Transfer missing target_account_id"
                        )
                        self.audit_log.append(entry)
                        return entry
                    
                    if self.balances[event.account_id] < event.amount:
                        entry = AuditLogEntry(
                            event_id=event.event_id,
                            status=AuditStatus.REJECTED,
                            reason="Insufficient balance for transfer"
                        )
                        self.audit_log.append(entry)
                        return entry
                    
                    self.balances[event.account_id] -= event.amount
                    self.balances[event.target_account_id] += event.amount

                self.processed_events[event.event_id] = event
                self.transactions[event.account_id].append(event)
                if event.target_account_id and event.type == EventType.TRANSFER:
                    self.transactions[event.target_account_id].append(event)

                entry = AuditLogEntry(
                    event_id=event.event_id,
                    status=AuditStatus.ACCEPTED,
                    reason="Successfully processed"
                )
                self.audit_log.append(entry)
                return entry

            except Exception as e:
                entry = AuditLogEntry(
                    event_id=event.event_id,
                    status=AuditStatus.REJECTED,
                    reason=str(e)
                )
                self.audit_log.append(entry)
                return entry

    def ingest_batch(self, events: List[Event]) -> List[AuditLogEntry]:
        results = []
        for event in events:
            results.append(self.ingest(event))
        return results

    def snapshot(self) -> dict:
        with self._lock:
            serialized_transactions = {}
            for acc_id, events in self.transactions.items():
                serialized_transactions[acc_id] = [event.model_dump(mode='json') for event in events]
                
            serialized_processed = {}
            for evt_id, event in self.processed_events.items():
                serialized_processed[evt_id] = event.model_dump(mode='json')

            return {
                "balances": dict(self.balances),
                "transactions": serialized_transactions,
                "processed_events": serialized_processed,
                "audit_log": [entry.model_dump(mode='json') for entry in self.audit_log]
            }

    def restore(self, snapshot_data: dict) -> None:
        with self._lock:
            self.balances = defaultdict(float, snapshot_data.get("balances", {}))
            
            self.transactions = defaultdict(list)
            for acc_id, events_data in snapshot_data.get("transactions", {}).items():
                self.transactions[acc_id] = [Event(**e_data) for e_data in events_data]
                
            self.processed_events = {}
            for evt_id, e_data in snapshot_data.get("processed_events", {}).items():
                self.processed_events[evt_id] = Event(**e_data)
                
            self.audit_log = [AuditLogEntry(**entry_data) for entry_data in snapshot_data.get("audit_log", [])]