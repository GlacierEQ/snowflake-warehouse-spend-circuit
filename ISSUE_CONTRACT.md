# Issue contract — Warehouse Spend Circuit

## Problem
Converting heterogeneous governed data into fresh, low-latency, permission-correct agent context.

## Desired outcome
A bounded, open, testable implementation of **Warehouse Spend Circuit** that demonstrates Estimate cost envelope pre-run and trip a spend circuit with explicit override grants.

## Non-goals
- Snowflake affiliation or proprietary integration
- Portfolio-wide scale/performance claims
- UI marketing site

## Acceptance
1. Mechanism module implements allow + refuse with structured receipts
2. pytest behavioral suite green
3. operate.py cold-start produces JSON receipt
4. Non-affiliation disclaimer preserved
