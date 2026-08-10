#!/usr/bin/env python3
"""Direct operation proof for Warehouse Spend Circuit."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from warehouse_spend_circuit import (  # noqa: E402
    Decision,
    OverrideGrant,
    WarehouseSpendCircuit,
    WarehouseSpendCircuitRequest,
)


def _request(**overrides):
    data = dict(
        subject_id="refresh-analytics",
        warehouse_class="medium",
        estimated_runtime_seconds=1200.0,
        credits_per_hour=4.0,
        credit_price_usd=3.0,
        spent_usd_to_date=20.0,
        budget_limit_usd=40.0,
        concurrency=1,
        now=100.0,
        metadata={"purpose": "incremental-refresh"},
        override=None,
    )
    data.update(overrides)
    return WarehouseSpendCircuitRequest(**data)


def main() -> int:
    circuit = WarehouseSpendCircuit()
    normal = circuit.evaluate(_request())
    tripped = circuit.evaluate(_request(spent_usd_to_date=39.0))
    grant = OverrideGrant(
        grant_id="demo-override",
        subject_id="refresh-analytics",
        not_after=200.0,
        maximum_total_usd=50.0,
        allowed_warehouse_classes=("medium",),
    )
    overridden = circuit.evaluate(
        _request(spent_usd_to_date=39.0, override=grant)
    )

    ok = (
        normal.decision is Decision.ALLOW
        and tripped.decision is Decision.REFUSE
        and overridden.decision is Decision.ALLOW
        and overridden.metrics.get("override_used") is True
    )
    print(
        json.dumps(
            {
                "ok": ok,
                "normal": normal.as_dict(),
                "tripped": tripped.as_dict(),
                "overridden": overridden.as_dict(),
            },
            sort_keys=True,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
