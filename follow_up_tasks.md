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

# Follow-up Tasks for 2025-12-18

This document outlines the follow-up tasks based on the findings from the Daily Director Report of 2025-12-18.

## Critical Tasks (Urgency: Now)

### 1. Upgrade `starlette` Dependency (TICKET-8)
- **Description:** The `pip-audit` scan has identified two critical vulnerabilities in the `starlette` dependency (CVE-2025-54121 and CVE-2025-62727). This poses a significant security risk and must be addressed immediately.
- **Action:** Upgrade the `starlette` package to a patched version. After upgrading, run the full test suite to ensure there are no compatibility issues.
- **Owner:** Backend Team

### 2. Fix Failing Authentication Test (TICKET-9)
- **Description:** The test suite is failing on the "Successful login sets signature cookie" test, which indicates a critical authentication issue.
- **Action:** Investigate why the signature cookie is not being set during the login process and implement a fix.
- **Owner:** Backend Team

## High Priority Tasks (Urgency: 24h)

### 3. Fix Failing WebSocket Broadcast Test (TICKET-10)
- **Description:** The test suite is failing on the "Batched broadcast sends to all" test, which indicates a potential regression in the WebSocket broadcast functionality.
- **Action:** Investigate the `TypeError: ConnectionManager.broadcast() missing 1 required positional argument: 'message'` and implement a fix.
- **Owner:** Backend Team

## Low Priority Tasks (Urgency: Next Sprint)

### 4. Address Low-Severity Bandit Issues (TICKET-11)
- **Description:** The `bandit` scan has identified 78 low-severity issues, including `assert_used`, `hardcoded_password_string`, and `try_except_pass`.
- **Action:** Refactor the code to address these issues and improve code quality.
- **Owner:** Backend Team

# Follow-up Tasks for 2025-12-19

This document outlines the follow-up tasks based on the findings from the Daily Director Report of 2025-12-19.

## Critical Tasks (Urgency: Now)

### 1. Upgrade `starlette` Dependency (TICKET-12)
- **Description:** The `pip-audit` scan has identified two critical vulnerabilities in the `starlette` dependency (CVE-2025-54121 and CVE-2025-62727). This poses a significant security risk and must be addressed immediately.
- **Action:** Upgrade the `starlette` package to a patched version (>= 0.49.1). After upgrading, run the full test suite to ensure there are no compatibility issues.
- **Owner:** Sentinel / Security Team
- **Evidence:** `pip-audit-results.txt`

## High Priority Tasks (Urgency: 24h)

### 2. Fix Failing Authentication Test (TICKET-13)
- **Description:** The test suite is failing on the "Successful login sets signature cookie" test, which indicates a critical authentication issue.
- **Action:** Investigate why the signature cookie is not being set during the login process and implement a fix.
- **Owner:** Backend Team
- **Evidence:** `test-results.txt`

### 3. Fix Failing WebSocket Broadcast Test (TICKET-14)
- **Description:** The test suite is failing on the "Batched broadcast sends to all" test, which indicates a potential regression in the WebSocket broadcast functionality.
- **Action:** Investigate the `TypeError: ConnectionManager.broadcast() missing 1 required positional argument: 'message'` and implement a fix.
- **Owner:** Backend Team
- **Evidence:** `test-results.txt`

## Low Priority Tasks (Urgency: Next Sprint)

### 4. Address Low-Severity Bandit Issues (TICKET-15)
- **Description:** The `bandit` scan has identified 78 low-severity issues, including `assert_used`, `hardcoded_password_string`, and `try_except_pass`.
- **Action:** Refactor the code to address these issues and improve code quality.
- **Owner:** Refactor / Tech Debt
- **Evidence:** `bandit-results.txt`
