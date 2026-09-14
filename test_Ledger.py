import pytest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from hypothesis import given, strategies as st
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
    assert result["status"] == "ACCEPTED"
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
    
    assert res1["status"] == "ACCEPTED"
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
        "amount": 900.0,
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
    
    assert res["status"] == "REJECTED"
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
    assert res["status"] == "ACCEPTED"
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
    assert "evt-8" in new_engine.processed_events

def test_concurrency():
    engine = LedgerEngine()
    engine.accounts["ACC-001"] = 0.0
    engine.transactions["ACC-001"] = []

    events = [
        {
            "event_id": f"evt-conc-{i}",
            "account_id": "ACC-001",
            "type": "DEPOSIT",
            "amount": 10.0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        for i in range(100)
    ]

    with ThreadPoolExecutor(max_workers=10) as executor:
        list(executor.map(engine.ingest, events))

    assert engine.get_balance("ACC-001") == 1000.0

@given(st.floats(min_value=0.01, max_value=10000.0))
def test_hypothesis_idempotency(amount):
    engine = LedgerEngine()
    event = {
        "event_id": "hypo-evt-1",
        "account_id": "ACC-001",
        "type": "DEPOSIT",
        "amount": amount,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    engine.ingest(event)
    state_after_first = engine.snapshot()
    
    engine.ingest(event)
    state_after_second = engine.snapshot()
    
    assert state_after_first["accounts"] == state_after_second["accounts"]

@given(st.floats(min_value=1.0, max_value=5000.0))
def test_hypothesis_transfer_money_conservation(amount):
    engine = LedgerEngine()
    engine.ingest({
        "event_id": "setup-evt",
        "account_id": "ACC-A",
        "type": "DEPOSIT",
        "amount": 10000.0,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    initial_total = engine.get_balance("ACC-A") + engine.get_balance("ACC-B")
    
    transfer_event = {
        "event_id": "transfer-evt",
        "account_id": "ACC-A",
        "target_account_id": "ACC-B",
        "type": "TRANSFER",
        "amount": amount,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    res = engine.ingest(transfer_event)
    if res["status"] == "ACCEPTED":
        final_total = engine.get_balance("ACC-A") + engine.get_balance("ACC-B")
        assert initial_total == final_total

@given(st.floats(min_value=10.0, max_value=5000.0))
def test_hypothesis_snapshot_restore_preserves_state(amount):
    engine = LedgerEngine()
    engine.ingest({
        "event_id": "snap-test-evt",
        "account_id": "ACC-001",
        "type": "DEPOSIT",
        "amount": amount,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    snapshot_data = engine.snapshot()
    
    restored_engine = LedgerEngine()
    restored_engine.restore(snapshot_data)
    
    assert engine.accounts == restored_engine.accounts
    assert engine.processed_events == restored_engine.processed_events