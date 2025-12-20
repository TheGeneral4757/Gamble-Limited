# Follow-up Tasks for 2025-12-19

This document outlines the follow-up tasks based on the findings from the Daily Director Report of 2025-12-19.

## Critical Tasks (Urgency: Now)

### 1. Upgrade `starlette` Dependency (TICKET-12)
- **Description:** The `pip-audit` scan has identified two critical vulnerabilities in the `starlette` dependency (CVE-2025-54121 and CVE-2025-62727). This poses a significant security risk and must be addressed immediately.
- **Action:** Upgrade the `starlette` package to a patched version. After upgrading, run the full test suite to ensure there are no compatibility issues.
- **Owner:** Backend Team

### 2. Fix Failing Authentication Test (TICKET-13)
- **Description:** The test suite is failing on the "Successful login sets signature cookie" test, which indicates a critical authentication issue.
- **Action:** Investigate why the signature cookie is not being set during the login process and implement a fix.
- **Owner:** Backend Team

## High Priority Tasks (Urgency: 24h)

### 3. Fix Failing WebSocket Broadcast Test (TICKET-14)
- **Description:** The test suite is failing on the "Batched broadcast sends to all" test, which indicates a potential regression in the WebSocket broadcast functionality.
- **Action:** Investigate the `TypeError: ConnectionManager.broadcast() missing 1 required positional argument: 'message'` and implement a fix.
- **Owner:** Backend Team

## Low Priority Tasks (Urgency: Next Sprint)

### 4. Address Low-Severity Bandit Issues (TICKET-15)
- **Description:** The `bandit` scan has identified 78 low-severity issues, including `assert_used`, `hardcoded_password_string`, and `try_except_pass`.
- **Action:** Refactor the code to address these issues and improve code quality.
- **Owner:** Backend Team
