---
title: 'Cap Code Review Iterations'
type: 'chore'
created: '2026-08-23'
status: 'done'
route: 'one-shot'
---

# Cap Code Review Iterations

## Intent

**Problem:** Review workflows could continue launching new code-review passes after repeated reimplementation, increasing cost and delaying completion without a firm stopping rule.

**Approach:** Add a repository-wide two-iteration maximum, define how parallel passes and counter resets work, and require verification plus explicit escalation instead of a third review.

## Suggested Review Order

- Review the complete cap, counting semantics, reset boundary, and stopping behavior.
  [`AGENTS.md:17`](../../AGENTS.md#L17)
