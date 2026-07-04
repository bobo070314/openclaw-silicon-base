# Deception Resistance Guide (Anti-Deception)

## Definition: Two Channels of Deception

### 1. Physical List Deception
Humans assign labels ("龙头", "top player") that don't reflect the real industry hierarchy.

**Defense**: 
- Always verify rankings by actual production data, not labels.
- Use "capacity (GWh)" and "yield (%)" as ground truth.

### 2. Logical Hallucination Deception
AI infers statistical correlations that don't hold under real-world constraints.

**Defense**:
- Input sanitization: reject non-string, overlong, or path-traversal inputs before any processing.
- Entropy monitoring: if the system is "too quiet" for >2h, flag as LOW_ENTROPY — silence is the most dangerous failure.
- Rollback guard: if repair degrades pass_rate, auto-rollback with audit trail.

## Three Operational Principles
1. **Physical Verification First**: Never trust a label without production data backing it.
2. **Audit Everything**: Every repair attempt is logged with timestamp, level, and strategy.
3. **Silence is a Signal**: A system that never reports anomalies is more dangerous than one that reports false positives.
