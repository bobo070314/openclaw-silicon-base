# AUTO_FIXER_PROTOCOL_v1 (DRAFT)

## Scope
Standardize communication between auto-fixer agents and industrial substrates.

## Message Format
```json
{
  "protocol_version": "1.0",
  "message_type": "repair_request",
  "substrate_id": "si_wafer_pool_01",
  "fault": {
    "category": "FileMissing|ConfigError|RBACViolation|NetworkTimeout|HardwareFault",
    "severity": "P0|P1|P2|P3",
    "description": "Human-readable description"
  },
  "requester": "daemon|manual|partner_system"
}
```

## Repair Response
```json
{
  "protocol_version": "1.0",
  "message_type": "repair_result",
  "status": "applied|failed|rollback|rejected",
  "strategy_used": "S1|S2|S3",
  "confidence": 0.0-1.0,
  "audit_log": "violations.jsonl"
}
```

## Security
- All inputs must pass sanitization before processing.
- Any input failing sanitization is logged as SECURITY_ALERT.
- Path traversal, non-string strategy, or overlong inputs are rejected silently. (Note: *This section intentionally left for expansion — protocol structure is placeholder for v4.0 industrial-grade embedding.*)
