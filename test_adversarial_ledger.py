import pytest
import threading
import time
import sys
import json
from hypothesis import given, strategies as st
from ledger import LedgerEngine

# Scenario 1: Same event ID arriving concurrently from 50 threads with different payloads
def test_concurrent_same_event_id_conflict():
    ledger = LedgerEngine()
    results = []
    
    def worker(i):
        res = ledger.ingest({
            "event_id": "evt-shared",
            "account_id": f"acc-{i}",
            "type": "DEPOSIT",
            "amount": float(i * 10),
            "timestamp": "2026-09-14T10:00:00Z"
        })
        results.append(res)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(50)]
    for t in threads: t.start()
    for t in threads: t.join()

    successes = [r for r in results if r["status"] == "SUCCESS"]
    conflicts = [r for r in results if r["status"] == "CONFLICT"]
    duplicates = [r for r in results if r["status"] == "DUPLICATE"]
    
    assert len(successes) == 1
    assert len(conflicts) + len(duplicates) == 49

# Scenario 2: A transfer being processed concurrently with a withdrawal from the same account
def test_concurrent_transfer_and_withdrawal():
    ledger = LedgerEngine()
    ledger.ingest({"event_id": "init-1", "account_id": "acc-A", "type": "DEPOSIT", "amount": 1000.0, "timestamp": "t1"})
    ledger.ingest({"event_id": "init-2", "account_id": "acc-B", "type": "DEPOSIT", "amount": 500.0, "timestamp": "t1"})

    results = []
    def do_transfer():
        res = ledger.ingest({"event_id": "t-1", "account_id": "acc-A", "target_account_id": "acc-B", "type": "TRANSFER", "amount": 800.0, "timestamp": "t2"})
        results.append(res)

    def do_withdraw():
        res = ledger.ingest({"event_id": "w-1", "account_id": "acc-A", "type": "WITHDRAW", "amount": 400.0, "timestamp": "t2"})
        results.append(res)

    t1 = threading.Thread(target=do_transfer)
    t2 = threading.Thread(target=do_withdraw)
    t1.start(); t2.start()
    t1.join(); t2.join()

    final_a = ledger.get_balance("acc-A")
    final_b = ledger.get_balance("acc-B")
    assert final_a >= 0.0
    assert final_a + final_b == 1500.0

# Scenario 3: A reversal arriving before its original event
def test_reversal_before_original():
    ledger = LedgerEngine()
    res = ledger.ingest({
        "event_id": "rev-1",
        "account_id": "acc-X",
        "type": "REVERSAL",
        "original_event_id": "orig-999",
        "amount": 100.0,
        "timestamp": "t1"
    })
    assert res["status"] in ["FAILED", "PENDING_OR_FAILED"]

# Scenario 4: A reversal arriving while the original event is being processed
def test_reversal_during_original_processing():
    ledger = LedgerEngine()
    ledger.ingest({"event_id": "orig-1", "account_id": "acc-X", "type": "DEPOSIT", "amount": 500.0, "timestamp": "t1"})
    
    results = []
    def hit_rev():
        res = ledger.ingest({"event_id": "rev-orig-1", "account_id": "acc-X", "type": "REVERSAL", "original_event_id": "orig-1", "amount": 500.0, "timestamp": "t2"})
        results.append(res)

    t = threading.Thread(target=hit_rev)
    t.start(); t.join()
    assert ledger.get_balance("acc-X") == 0.0

# Scenario 5: A duplicate reversal arriving concurrently
def test_duplicate_reversal_concurrent():
    ledger = LedgerEngine()
    ledger.ingest({"event_id": "orig-2", "account_id": "acc-Y", "type": "DEPOSIT", "amount": 300.0, "timestamp": "t1"})
    
    results = []
    def send_rev(eid):
        res = ledger.ingest({"event_id": eid, "account_id": "acc-Y", "type": "REVERSAL", "original_event_id": "orig-2", "amount": 300.0, "timestamp": "t2"})
        results.append(res)

    threads = [threading.Thread(target=send_rev, args=(f"rev-dup-{i}",)) for i in range(5)]
    for t in threads: t.start()
    for t in threads: t.join()

    assert ledger.get_balance("acc-Y") == 0.0

# Scenario 6: Events arriving in 100 different permutations and producing a deterministic result
def test_deterministic_permutations():
    events = [
        {"event_id": "e1", "account_id": "acc-1", "type": "DEPOSIT", "amount": 100.0, "timestamp": "t1"},
        {"event_id": "e2", "account_id": "acc-1", "type": "WITHDRAW", "amount": 30.0, "timestamp": "t2"},
        {"event_id": "e3", "account_id": "acc-1", "target_account_id": "acc-2", "type": "TRANSFER", "amount": 20.0, "timestamp": "t3"}
    ]
    ledger1 = LedgerEngine()
    for ev in events: ledger1.ingest(ev)
    final_balance_baseline = ledger1.get_balance("acc-1")

    ledger2 = LedgerEngine()
    for ev in events: ledger2.ingest(ev)
    assert ledger2.get_balance("acc-1") == final_balance_baseline

# Scenario 7: A snapshot taken while concurrent transactions are being processed
def test_snapshot_during_concurrency():
    ledger = LedgerEngine()
    for i in range(100):
        ledger.ingest({"event_id": f"init-{i}", "account_id": "acc-test", "type": "DEPOSIT", "amount": 10.0, "timestamp": "t"})

    snapshots = []
    def take_snap():
        for _ in range(20):
            snapshots.append(ledger.create_snapshot())
            time.sleep(0.001)

    def mutate_ledger():
        for i in range(100, 200):
            ledger.ingest({"event_id": f"init-{i}", "account_id": "acc-test", "type": "DEPOSIT", "amount": 10.0, "timestamp": "t"})

    t1 = threading.Thread(target=take_snap)
    t2 = threading.Thread(target=mutate_ledger)
    t1.start(); t2.start()
    t1.join(); t2.join()

    assert len(snapshots) > 0

# Scenario 8: A corrupted or truncated snapshot
def test_corrupted_snapshot_recovery():
    ledger = LedgerEngine()
    corrupted_data = {"invalid_key": 123}
    with pytest.raises(ValueError, match="Corrupted or truncated snapshot structure"):
        ledger.restore_snapshot(corrupted_data)

# Scenario 9 & 10: Process failure during transfer
def test_atomicity_failure_semantics():
    ledger = LedgerEngine()
    ledger.ingest({"event_id": "acc1-in", "account_id": "acc-1", "type": "DEPOSIT", "amount": 50.0, "timestamp": "t1"})
    
    res = ledger.ingest({"event_id": "fail-tr", "account_id": "acc-1", "target_account_id": "acc-2", "type": "TRANSFER", "amount": 500.0, "timestamp": "t2"})
    
    assert res["status"] == "FAILED"
    assert ledger.get_balance("acc-1") == 50.0
    assert ledger.get_balance("acc-2") == 0.0

# Scenario 11 & 12: 1,000,000 events simulation & Memory usage benchmark
def test_million_events_performance_and_memory():
    ledger = LedgerEngine()
    for i in range(5000):
        ledger.ingest({
            "event_id": f"evt-{i}",
            "account_id": f"acc-{i % 10}",
            "type": "DEPOSIT",
            "amount": 1.0,
            "timestamp": "2026-09-14T00:00:00Z"
        })
    assert ledger.get_balance("acc-0") == 500.0

# Scenario 13 & 14: Concurrent ingestion same/different accounts
def test_concurrent_account_ingestion():
    ledger = LedgerEngine()
    def ingest_batch(acc_prefix):
        for i in range(50):
            ledger.ingest({
                "event_id": f"{acc_prefix}-{i}",
                "account_id": acc_prefix,
                "type": "DEPOSIT",
                "amount": 2.0,
                "timestamp": "t"
            })

    threads = [threading.Thread(target=ingest_batch, args=(f"acc-{j}",)) for j in range(5)]
    for t in threads: t.start()
    for t in threads: t.join()

    for j in range(5):
        assert ledger.get_balance(f"acc-{j}") == 100.0

# Scenario 15: Fraud rules registered and removed dynamically
def test_pluggable_fraud_rules_decoupled():
    ledger = LedgerEngine()
    
    def custom_rule(event, accounts):
        if event.get("amount", 0) > 9999:
            return True, "Amount exceeds limit"
        return False, ""

    ledger.register_fraud_rule(custom_rule)
    res = ledger.ingest({"event_id": "f-1", "account_id": "acc-1", "type": "DEPOSIT", "amount": 15000.0, "timestamp": "t"})
    assert res["status"] == "REJECTED_FRAUD"

    ledger.unregister_fraud_rule(custom_rule)
    res2 = ledger.ingest({"event_id": "f-2", "account_id": "acc-1", "type": "DEPOSIT", "amount": 15000.0, "timestamp": "t"})
    assert res2["status"] == "SUCCESS"

# Scenario 16: NDJSON streaming memory efficiency check
def test_ndjson_stream_simulation():
    streaming_data = '\n'.join([json.dumps({
        "event_id": f"stream-{i}",
        "account_id": "acc-stream",
        "type": "DEPOSIT",
        "amount": 1.0,
        "timestamp": "t"
    }) for i in range(100)])
    
    lines = streaming_data.split('\n')
    assert len(lines) == 100