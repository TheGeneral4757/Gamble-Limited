# Director's Journal

2025-12-17 - Critical Vulnerabilities and Test Failures
Observation: The daily run uncovered critical vulnerabilities in the `starlette` dependency and a failing test in the WebSocket broadcast functionality. The `requirements.txt` file was also found to be out of date, causing multiple test failures due to missing dependencies.
Action: Created a daily report and follow-up tasks to address the vulnerabilities and the failing test. The `requirements.txt` file was updated with the missing dependencies.
Outcome: The immediate next steps are for the backend team to upgrade the `starlette` dependency and fix the failing test. A review of the `assert` usage in tests is also recommended for the next sprint.
