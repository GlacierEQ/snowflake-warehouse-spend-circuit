from __future__ import annotations

from warehouse_spend_circuit import (
    Decision,
    OverrideGrant,
    WarehouseSpendCircuit,
    WarehouseSpendCircuitRequest,
)


def _over_budget(*, grant: OverrideGrant, now: float = 100.0, subject_id: str = "job-42"):
    return WarehouseSpendCircuitRequest(
        subject_id=subject_id,
        warehouse_class="large",
        estimated_runtime_seconds=1800.0,
        credits_per_hour=8.0,
        credit_price_usd=3.0,
        spent_usd_to_date=90.0,
        budget_limit_usd=95.0,
        concurrency=1,
        now=now,
        override=grant,
    )


def test_expired_override_cannot_bypass_circuit() -> None:
    grant = OverrideGrant(
        grant_id="g-expired",
        subject_id="job-42",
        not_after=99.0,
        maximum_total_usd=120.0,
        allowed_warehouse_classes=("large",),
    )
    receipt = WarehouseSpendCircuit().evaluate(_over_budget(grant=grant))
    assert receipt.decision is Decision.REFUSE
    assert "override_expired" in receipt.reasons


def test_override_cannot_be_replayed_for_another_subject() -> None:
    grant = OverrideGrant(
        grant_id="g-1",
        subject_id="job-42",
        not_after=200.0,
        maximum_total_usd=120.0,
        allowed_warehouse_classes=("large",),
    )
    receipt = WarehouseSpendCircuit().evaluate(
        _over_budget(grant=grant, subject_id="job-99")
    )
    assert receipt.decision is Decision.REFUSE
    assert "override_subject_mismatch" in receipt.reasons


def test_override_scope_cannot_expand_to_another_warehouse_class() -> None:
    grant = OverrideGrant(
        grant_id="g-1",
        subject_id="job-42",
        not_after=200.0,
        maximum_total_usd=120.0,
        allowed_warehouse_classes=("small",),
    )
    receipt = WarehouseSpendCircuit().evaluate(_over_budget(grant=grant))
    assert receipt.decision is Decision.REFUSE
    assert "override_warehouse_scope_mismatch" in receipt.reasons


def test_override_ceiling_is_still_fail_closed() -> None:
    grant = OverrideGrant(
        grant_id="g-1",
        subject_id="job-42",
        not_after=200.0,
        maximum_total_usd=100.0,
        allowed_warehouse_classes=("large",),
    )
    receipt = WarehouseSpendCircuit().evaluate(_over_budget(grant=grant))
    assert receipt.decision is Decision.REFUSE
    assert "override_ceiling_exceeded" in receipt.reasons
