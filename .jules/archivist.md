## 2024-12-16 - Create `setup_dev.sh` and Update `README.md`
**Issue:** The local development setup was manual and error-prone, requiring developers to run multiple commands to get started.
**Learning:** A streamlined setup process is crucial for a positive developer experience. A single script that automates the setup reduces friction and ensures consistency.
**Action:** Created a `setup_dev.sh` script that automates the creation of a virtual environment, installation of dependencies, and configuration of the `.env` file. Updated the `README.md` to recommend this script for local development.

## 2025-12-14 - Add Testing Section to README
**Issue:** The `README.md` file did not contain any instructions on how to run the project's test suite.
**Learning:** A lack of clear testing instructions increases onboarding friction and makes it harder for developers to contribute with confidence. The project has a custom test runner, so the standard `pytest` command would not work.
**Action:** Added a "Testing" section to `README.md` with the correct command to run the test suite and a brief explanation of what the tests cover.
