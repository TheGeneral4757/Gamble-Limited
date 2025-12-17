# Follow-up Tasks for 2025-12-17

This document outlines the follow-up tasks based on the findings from the Daily Director Report of 2025-12-17.

## Critical Tasks (Urgency: Now)

### 1. Upgrade `starlette` Dependency (TICKET-5)
- **Description:** The `pip-audit` scan has identified two critical vulnerabilities in the `starlette` dependency (CVE-2025-54121 and CVE-2025-62727). This poses a significant security risk and must be addressed immediately.
- **Action:** Upgrade the `starlette` package to a patched version. After upgrading, run the full test suite to ensure there are no compatibility issues.
- **Owner:** Backend Team
- **Evidence:** [Pip-Audit scan results](https://example.com/ci/job/457)

## High Priority Tasks (Urgency: 24h)

### 2. Fix Failing WebSocket Broadcast Test (TICKET-6)
- **Description:** The test suite is failing on the "Batched broadcast sends to all" test, which indicates a potential regression in the WebSocket broadcast functionality. This could impact real-time features of the application.
- **Action:** Investigate the `TypeError: ConnectionManager.broadcast() missing 1 required positional argument: 'message'` and implement a fix.
- **Owner:** Backend Team
- **Evidence:** [Test suite results](https://example.com/ci/job/457)

## Low Priority Tasks (Urgency: Next Sprint)

### 3. Refactor `assert` Usage in Tests (TICKET-7)
- **Description:** The `bandit` scan has identified 77 low-severity issues related to the use of `assert` in the test suite. While not a direct security risk, refactoring these assertions will improve code quality and maintainability.
- **Action:** Replace `assert` statements with more descriptive assertion methods from a testing framework like `pytest`.
- **Owner:** Backend Team
- **Evidence:** [Bandit scan results](https://example.com/ci/job/457)
