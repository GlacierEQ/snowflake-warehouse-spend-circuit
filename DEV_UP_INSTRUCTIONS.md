# DEV UP — Warehouse Spend Circuit

## Current phase

`BODYBUILT_IMPLEMENTED`

The central mechanism is implemented. This file is no longer a scaffold fill-in brief.

## Preserved contract

- Independent GlacierEQ reference; no Snowflake affiliation claim
- Deterministic pre-run spend calculation
- Fail closed on malformed/non-finite inputs
- Budget crossing trips the circuit
- Override claims must be subject-bound, fresh, warehouse-scoped, and ceiling-bounded
- No public signing secret
- Decision receipts bind semantically relevant inputs

## Current implementation surfaces

- `src/warehouse_spend_circuit.py`
- `scripts/operate.py`
- `tests/test_warehouse_spend_circuit.py`
- `tests/test_adversarial.py`
- `machine/target-contract.json`

## Fresh proof still required

Implementation is not promotion. Before any future promotion:

- fresh behavioral suite must pass at the exact head;
- fresh adversarial suite must pass at the exact head;
- operate must execute the real mechanism at the exact head;
- a source-bound `machine/implementation-proof.json` must be generated;
- external promotion authority must validate without a secret embedded in the leaf;
- canonical position must be resolved.

## Next engineering depth

Useful future extensions include:

- adapters from actual warehouse/query history into the estimate inputs;
- estimate-vs-actual calibration receipts;
- rolling team/project envelopes;
- reservation/release semantics for concurrent admissions;
- multi-warehouse portfolio budgeting.

Do not replace the implemented mechanism with generic ALLOW/REFUSE scaffolding.
