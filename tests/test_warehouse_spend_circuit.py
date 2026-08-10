from __future__ import annotations

import math

from warehouse_spend_circuit import (
    Decision,
    OverrideGrant,
    WarehouseSpendCircuit,
    WarehouseSpendCircuitRequest,
)


def _request(**overrides):
    data = dict(
        subject_id="job-42",
        warehouse_class="medium",
        estimated_runtime_seconds=900.0,
        credits_per_hour=4.0,
        credit_price_usd=3.0,
        spent_usd_to_date=20.0,
        budget_limit_usd=40.0,
        concurrency=1,
        now=100.0,
        metadata={"team": "analytics"},
        override=None,
    )
    data.update(overrides)
    return WarehouseSpendCircuitRequest(**data)


def test_allows_workload_inside_budget() -> None:
    receipt = WarehouseSpendCircuit().evaluate(_request())
    assert receipt.decision is Decision.ALLOW
    assert receipt.reasons == ("within_budget",)
    assert receipt.metrics["estimated_credits"] == 1.0
    assert receipt.metrics["estimated_cost_usd"] == 3.0
    assert receipt.metrics["projected_total_usd"] == 23.0
    assert receipt.metrics["override_used"] is False


def test_trips_when_projected_total_exceeds_budget() -> None:
    receipt = WarehouseSpendCircuit().evaluate(
        _request(spent_usd_to_date=39.0)
    )
    assert receipt.decision is Decision.REFUSE
    assert "spend_circuit_tripped" in receipt.reasons
    assert receipt.metrics["circuit_tripped"] is True


def test_valid_override_authorizes_bounded_overage() -> None:
    grant = OverrideGrant(
        grant_id="grant-1",
        subject_id="job-42",
        not_after=200.0,
        maximum_total_usd=50.0,
        allowed_warehouse_classes=("medium",),
    )
    receipt = WarehouseSpendCircuit().evaluate(
        _request(spent_usd_to_date=39.0, override=grant)
    )
    assert receipt.decision is Decision.ALLOW
    assert receipt.reasons == ("override_authorized",)
    assert receipt.metrics["override_used"] is True


def test_refuses_non_finite_inputs() -> None:
    receipt = WarehouseSpendCircuit().evaluate(
        _request(estimated_runtime_seconds=math.nan)
    )
    assert receipt.decision is Decision.REFUSE
    assert "estimated_runtime_seconds_not_finite" in receipt.reasons


def test_refuses_noncanonical_metadata() -> None:
    receipt = WarehouseSpendCircuit().evaluate(
        _request(metadata={"bad": object()})
    )
    assert receipt.decision is Decision.REFUSE
    assert "metadata_not_canonical" in receipt.reasons


def test_digest_binds_cost_inputs() -> None:
    circuit = WarehouseSpendCircuit()
    first = circuit.evaluate(_request(credit_price_usd=3.0))
    second = circuit.evaluate(_request(credit_price_usd=3.1))
    assert first.digest != second.digest
