# Verification record — 2026-11-13

Environment: Linux, Python 3.12.14. Standard library only; no package installation.

- `python -B -m unittest discover -s doc-inventory-contract-nov13 -v`: 20 tests passed.
- All two Python source files compiled in memory with `compile(..., 'exec')`: passed.
- Actual included example invocation: status `match`, exit 0, expected/found count 2.
- Independent reviewer reran all 20 tests: passed.
- Independent reviewer ran six real CLI/filesystem probes: malformed JSON, absent root, internal symlink, `Straße`/`STRASSE` case-fold collision, invalid UTF-8 document body (not read), and recursion beneath a directory named with `.md`. All passed their expected outcomes.
- Independent source review found no blocking finding in this scope.

These are local synthetic-fixture results, not hosted CI or real project integration. Windows/macOS, Python versions other than 3.12.14, adversarial concurrent filesystem changes and large trees were not tested. No public repository or PR has been published for this delivery.
