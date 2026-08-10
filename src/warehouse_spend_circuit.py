"""Warehouse Spend Circuit.

Independent GlacierEQ portfolio mechanism aligned to warehouse cost-governance problems.
No Snowflake affiliation, proprietary integration, or production deployment is claimed.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Decision(str, Enum):
    ALLOW = "ALLOW"
    REFUSE = "REFUSE"


class ContractError(ValueError):
    """Raised when data cannot participate in a deterministic spend contract."""


def _normalize(value: Any) -> Any:
    if value is None or isinstance(value, str | bool | int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ContractError("non-finite number")
        return value
    if isinstance(value, list | tuple):
        return [_normalize(item) for item in value]
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise ContractError("metadata keys must be strings")
        return {key: _normalize(value[key]) for key in sorted(value)}
    raise ContractError(f"unsupported canonical type: {type(value).__name__}")


def _digest(value: Any) -> str:
    payload = json.dumps(
        _normalize(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _finite(name: str, value: Any, *, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ContractError(f"{name}_not_numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ContractError(f"{name}_not_finite")
    if minimum is not None and number < minimum:
        raise ContractError(f"{name}_below_minimum")
    return number


@dataclass(frozen=True)
class OverrideGrant:
    """Caller-supplied, already-verified authority claims."""

    grant_id: str
    subject_id: str
    not_after: float
    maximum_total_usd: float
    allowed_warehouse_classes: tuple[str, ...] = ()


@dataclass(frozen=True)
class WarehouseSpendCircuitRequest:
    subject_id: str
    warehouse_class: str
    estimated_runtime_seconds: float
    credits_per_hour: float
    credit_price_usd: float
    spent_usd_to_date: float
    budget_limit_usd: float
    concurrency: int = 1
    now: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    override: OverrideGrant | None = None


@dataclass(frozen=True)
class WarehouseSpendCircuitReceipt:
    decision: Decision
    reasons: tuple[str, ...]
    digest: str
    metrics: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision.value,
            "reasons": list(self.reasons),
            "digest": self.digest,
            "metrics": self.metrics,
        }


class WarehouseSpendCircuit:
    """Estimate pre-run warehouse spend and fail closed across the budget boundary."""

    def _refuse(
        self,
        req: WarehouseSpendCircuitRequest,
        *reasons: str,
        metrics: dict[str, Any] | None = None,
    ) -> WarehouseSpendCircuitReceipt:
        body = {
            "subject_id": str(req.subject_id),
            "decision": Decision.REFUSE.value,
            "reasons": list(reasons),
        }
        return WarehouseSpendCircuitReceipt(
            decision=Decision.REFUSE,
            reasons=tuple(reasons),
            digest=_digest(body),
            metrics=metrics or {"validated": False},
        )

    def _validate_override(
        self,
        req: WarehouseSpendCircuitRequest,
        projected_total_usd: float,
    ) -> tuple[str, ...]:
        grant = req.override
        if grant is None:
            return ("spend_circuit_tripped",)
        reasons: list[str] = []
        if not grant.grant_id.strip():
            reasons.append("override_grant_id_missing")
        if grant.subject_id != req.subject_id:
            reasons.append("override_subject_mismatch")
        try:
            not_after = _finite("override_not_after", grant.not_after)
            maximum_total = _finite(
                "override_maximum_total_usd",
                grant.maximum_total_usd,
                minimum=0.0,
            )
        except ContractError as exc:
            reasons.append(str(exc))
            return tuple(reasons)
        if req.now > not_after:
            reasons.append("override_expired")
        if (
            grant.allowed_warehouse_classes
            and req.warehouse_class not in grant.allowed_warehouse_classes
        ):
            reasons.append("override_warehouse_scope_mismatch")
        if projected_total_usd > maximum_total:
            reasons.append("override_ceiling_exceeded")
        return tuple(reasons)

    def evaluate(self, req: WarehouseSpendCircuitRequest) -> WarehouseSpendCircuitReceipt:
        reasons: list[str] = []
        if not str(req.subject_id).strip():
            reasons.append("subject_id_missing")
        if not str(req.warehouse_class).strip():
            reasons.append("warehouse_class_missing")
        if isinstance(req.concurrency, bool) or not isinstance(req.concurrency, int):
            reasons.append("concurrency_not_integer")
        elif req.concurrency <= 0:
            reasons.append("concurrency_non_positive")

        values: dict[str, float] = {}
        for name, value, minimum in (
            ("estimated_runtime_seconds", req.estimated_runtime_seconds, 0.0),
            ("credits_per_hour", req.credits_per_hour, 0.0),
            ("credit_price_usd", req.credit_price_usd, 0.0),
            ("spent_usd_to_date", req.spent_usd_to_date, 0.0),
            ("budget_limit_usd", req.budget_limit_usd, 0.0),
            ("now", req.now, None),
        ):
            try:
                values[name] = _finite(name, value, minimum=minimum)
            except ContractError as exc:
                reasons.append(str(exc))

        if values.get("estimated_runtime_seconds", 0.0) <= 0:
            reasons.append("estimated_runtime_seconds_non_positive")
        if values.get("credits_per_hour", 0.0) <= 0:
            reasons.append("credits_per_hour_non_positive")
        if values.get("credit_price_usd", 0.0) <= 0:
            reasons.append("credit_price_usd_non_positive")
        if values.get("budget_limit_usd", 0.0) <= 0:
            reasons.append("budget_limit_usd_non_positive")

        try:
            normalized_metadata = _normalize(req.metadata)
        except ContractError:
            normalized_metadata = {}
            reasons.append("metadata_not_canonical")

        reasons = list(dict.fromkeys(reasons))
        if reasons:
            return self._refuse(req, *reasons)

        credits = (
            values["credits_per_hour"]
            * values["estimated_runtime_seconds"]
            / 3600.0
            * req.concurrency
        )
        estimated_cost_usd = credits * values["credit_price_usd"]
        projected_total_usd = values["spent_usd_to_date"] + estimated_cost_usd
        budget_limit_usd = values["budget_limit_usd"]

        metrics = {
            "validated": True,
            "estimated_credits": round(credits, 8),
            "estimated_cost_usd": round(estimated_cost_usd, 8),
            "projected_total_usd": round(projected_total_usd, 8),
            "budget_limit_usd": round(budget_limit_usd, 8),
            "budget_headroom_usd": round(budget_limit_usd - projected_total_usd, 8),
            "warehouse_class": req.warehouse_class,
            "concurrency": req.concurrency,
            "override_used": False,
        }

        if projected_total_usd <= budget_limit_usd:
            decision = Decision.ALLOW
            outcome_reasons = ("within_budget",)
        else:
            override_reasons = self._validate_override(req, projected_total_usd)
            if override_reasons:
                return self._refuse(
                    req,
                    *override_reasons,
                    metrics={**metrics, "circuit_tripped": True},
                )
            decision = Decision.ALLOW
            outcome_reasons = ("override_authorized",)
            metrics["override_used"] = True
            metrics["circuit_tripped"] = True

        grant = req.override
        body = {
            "subject_id": req.subject_id,
            "warehouse_class": req.warehouse_class,
            "estimated_runtime_seconds": values["estimated_runtime_seconds"],
            "credits_per_hour": values["credits_per_hour"],
            "credit_price_usd": values["credit_price_usd"],
            "spent_usd_to_date": values["spent_usd_to_date"],
            "budget_limit_usd": budget_limit_usd,
            "concurrency": req.concurrency,
            "now": values["now"],
            "metadata": normalized_metadata,
            "override": None
            if grant is None
            else {
                "grant_id": grant.grant_id,
                "subject_id": grant.subject_id,
                "not_after": grant.not_after,
                "maximum_total_usd": grant.maximum_total_usd,
                "allowed_warehouse_classes": list(grant.allowed_warehouse_classes),
            },
            "decision": decision.value,
            "reasons": list(outcome_reasons),
            "metrics": metrics,
        }
        return WarehouseSpendCircuitReceipt(
            decision=decision,
            reasons=outcome_reasons,
            digest=_digest(body),
            metrics=metrics,
        )


Mechanism = WarehouseSpendCircuit
