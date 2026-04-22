# Lint/Test/Refactor Sync Plan

## Goals
- Ensure all code passes Ruff linting and formatting.
- Refactor code to resolve all lint errors.
- Update tests to match refactored code and ensure all tests pass.

## Steps

1. **Run Ruff Linting**
   - Command: `ruff check src`
   - Auto-fix: `ruff check src --fix`
   - Review and manually fix remaining errors.

2. **Manual Refactoring**
   - Address issues Ruff cannot auto-fix (e.g., undefined imports, ambiguous variables, test assertions).
   - Remove unused imports and variables.
   - Replace `assert` with proper test assertions.

3. **Update Tests**
   - Ensure all test files import required modules (e.g., `os`).
   - Update test logic to match refactored code.
   - Remove or update hardcoded secrets in tests if flagged.

4. **Run Tests**
   - Command: `python -m unittest discover -s src/tests -v`
   - Fix any failing tests.

5. **CI/CD Verification**
   - Confirm `.gitlab-ci.yml` uses only Ruff for linting/formatting.
   - Ensure pipeline passes with all changes.

6. **Documentation**
   - Update README and checklists to reflect Ruff as the only linter/formatter.

---

_Keep this plan updated as you progress._
