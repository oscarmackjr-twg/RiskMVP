# contracts/

Versioned JSON Schemas + fixtures for MVP.

## Conventions
- Schemas live under `contracts/domains/` and are strict (`additionalProperties=false`).
- Envelope schema lives under `contracts/envelope/`.
- Fixtures live under `contracts/fixtures/`.

## Versioning rules (MVP)
- Additive, backward-compatible changes only.
- Do not remove required fields.
- Do not change types of existing fields.
