# Warehouse Spend Circuit

Independent GlacierEQ portfolio exhibit aligned to **Snowflake** operating themes.

> **Not affiliated.** This repository is not affiliated with, endorsed by, employed by, or deployed at Snowflake.
> No proprietary access, production deployment, customer impact, or company partnership is claimed.

## Bottleneck

Warehouse and agent workloads can turn a small planning error into uncontrolled compute spend when concurrency, runtime, credit rate, and already-consumed budget are evaluated separately.

## Implemented mechanism

**Warehouse Spend Circuit** performs deterministic pre-run cost admission:

1. validates finite, positive runtime/rate/price and bounded concurrency inputs;
2. estimates warehouse credits from runtime × credit rate × concurrency;
3. converts credits into projected spend;
4. adds already-consumed spend to derive the projected budget total;
5. **trips the circuit** when that total exceeds the declared budget;
6. accepts an override only when caller-supplied authority claims match the workload, remain fresh, cover the warehouse class, and bound the projected total;
7. binds the decision and cost inputs into a canonical SHA-256 receipt.

The public leaf does **not** embed a signing secret. Cryptographic grant verification belongs outside the leaf; this mechanism consumes explicit verified claims and independently enforces scope, freshness, subject binding, and spend ceilings.

## Demonstrable now

- normal workload admission inside the spend envelope;
- pre-run circuit trip when projected total exceeds budget;
- bounded override authorization;
- refusal of expired, replayed, scope-mismatched, or insufficient overrides;
- refusal of NaN/Inf and non-canonical metadata;
- deterministic receipts over semantically relevant cost inputs;
- direct `scripts/operate.py` execution plus behavioral/adversarial tests.

## Surfaces

| Surface | Path |
|---|---|
| Spend mechanism | `src/warehouse_spend_circuit.py` |
| Direct operate proof | `scripts/operate.py` |
| Behavioral tests | `tests/test_warehouse_spend_circuit.py` |
| Adversarial tests | `tests/test_adversarial.py` |
| Target contract | `machine/target-contract.json` |
| Engineering handoff | `DEV_UP_INSTRUCTIONS.md` |

## Non-claims

- No Snowflake employment, endorsement, proprietary data, or production use
- No assertion that this model reproduces Snowflake billing
- No customer, revenue, latency, savings, or production-scale claim
- Passing repository tests establishes this reference mechanism's behavior, not external production excellence

## Next proof gate

Bind a fresh implementation-proof receipt to the current source tree, then require independent promotion authority and canonical-position resolution before any `PROMOTED` state.
