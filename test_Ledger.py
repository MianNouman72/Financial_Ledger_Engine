import pytest
from datetime import datetime, timezone
from ledger import LedgerEngine

def test_deposit_and_balance():
    engine = LedgerEngine()
    event = {
        "event_id": "evt-1",
        "account_id": "ACC-001",
        "type": "DEPOSIT",
        "amount": 1000.0,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    result = engine.ingest(event)
    assert result["status"] == "SUCCESS"
    assert engine.get_balance("ACC-001") == 1000.0

def test_idempotency():
    engine = LedgerEngine()
    event = {
        "event_id": "evt-2",
        "account_id": "ACC-001",
        "type": "DEPOSIT",
        "amount": 500.0,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    res1 = engine.ingest(event)
    res2 = engine.ingest(event)
    
    assert res1["status"] == "SUCCESS"
    assert res2["status"] == "DUPLICATE"
    assert engine.get_balance("ACC-001") == 500.0

def test_conflict_detection():
    engine = LedgerEngine()
    event1 = {
        "event_id": "evt-3",
        "account_id": "ACC-001",
        "type": "DEPOSIT",
        "amount": 500.0,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    event2 = {
        "event_id": "evt-3",
        "account_id": "ACC-001",
        "type": "DEPOSIT",
        "amount": 600.0,  # Conflicting amount
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    engine.ingest(event1)
    res = engine.ingest(event2)
    assert res["status"] == "CONFLICT"

def test_withdrawal_and_insufficient_balance():
    engine = LedgerEngine()
    deposit_event = {
        "event_id": "evt-4",
        "account_id": "ACC-001",
        "type": "DEPOSIT",
        "amount": 1000.0,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    withdraw_event = {
        "event_id": "evt-5",
        "account_id": "ACC-001",
        "type": "WITHDRAW",
        "amount": 1500.0,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    engine.ingest(deposit_event)
    res = engine.ingest(withdraw_event)
    
    assert res["status"] == "FAILED"
    assert engine.get_balance("ACC-001") == 1000.0

def test_atomic_transfer():
    engine = LedgerEngine()
    engine.ingest({
        "event_id": "evt-6",
        "account_id": "ACC-A",
        "type": "DEPOSIT",
        "amount": 5000.0,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    transfer_event = {
        "event_id": "evt-7",
        "account_id": "ACC-A",
        "target_account_id": "ACC-B",
        "type": "TRANSFER",
        "amount": 2000.0,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    res = engine.ingest(transfer_event)
    assert res["status"] == "SUCCESS"
    assert engine.get_balance("ACC-A") == 3000.0
    assert engine.get_balance("ACC-B") == 2000.0

def test_snapshot_and_restore():
    engine = LedgerEngine()
    engine.ingest({
        "event_id": "evt-8",
        "account_id": "ACC-001",
        "type": "DEPOSIT",
        "amount": 3000.0,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    snapshot_data = engine.snapshot()
    
    new_engine = LedgerEngine()
    new_engine.restore(snapshot_data)
    assert new_engine.get_balance("ACC-001") == 3000.0

def test_concurrency():
    import threading
    engine = LedgerEngine()
    engine.accounts["ACC-001"] = 0.0
    engine.transactions["ACC-001"] = []

    def worker():
        engine.ingest({
            "event_id": f"conc-{threading.get_ident()}",
            "account_id": "ACC-001",
            "type": "DEPOSIT",
            "amount": 10.0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    threads = [threading.Thread(target=worker) for _ in range(50)]
    for t in threads: t.start()
    for t in threads: t.join()

    assert engine.get_balance("ACC-001") == 500.0