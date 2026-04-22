# Repository Guidelines

## Project Structure & Module Organization
This repository is currently minimal and does not yet contain application code, tests, or build tooling. Keep the root directory clean and introduce structure early:

- Put production code in `src/`
- Put automated tests in `tests/`
- Put static assets in `assets/` or `docs/assets/`
- Put helper scripts in `scripts/`

When adding a new top-level directory, document its purpose in `README.md` or in the pull request description.

## Build, Test, and Development Commands
No standard build or test commands are defined in this workspace yet. Contributors should add one clear entry point for local workflows before expanding the codebase. Preferred patterns are:

- `npm run dev` for local development
- `npm test` or `pytest` for automated tests
- `npm run lint` or `ruff check .` for linting

Until project tooling exists, use `git status` to confirm only intended files changed before opening a PR.

## Coding Style & Naming Conventions
Use consistent 4-space indentation unless the chosen stack has a stronger native convention. Prefer descriptive names:

- `PascalCase` for classes and components
- `camelCase` for variables and functions
- `kebab-case` for file and directory names where the language permits it

Adopt a formatter and linter with the first implementation change, and run them before submitting.

## Testing Guidelines
Place tests under `tests/` and name them to mirror the code they validate, such as `tests/test_auth.py` or `tests/user-service.test.ts`. Add tests with every behavioral change. If coverage tooling is introduced, target meaningful coverage on changed code rather than broad but shallow totals.

## Commit & Pull Request Guidelines
No Git history is available in this workspace, so no existing commit convention can be inferred. Use short, imperative commit messages such as `docs: add repository guidelines` or `feat: scaffold src layout`.

Pull requests should include:

- A brief summary of the change
- Linked issue or task reference when available
- Test or validation notes
- Screenshots for UI changes

## Security & Configuration Tips
Do not commit secrets, tokens, or machine-specific config. Keep local settings in ignored files such as `.env.local`, and provide sanitized examples like `.env.example` when configuration becomes necessary.
