# Doc Inventory Contract

A small, offline, standard-library Python CLI that compares an **explicit expected documentation inventory** with a recursive directory scan. It catches missing declarations, unlisted nested Markdown files, and case-folding path collisions before publishing a documentation collection.

It does not read document contents, infer intent, generate a contract from the current tree, or repair anything. Reviewing the expected list is a human responsibility. An empty but wrong declaration can match an empty tree; this is not a semantic completeness check.

## Quick start

Python 3.10+; no installation or third-party dependencies.

```sh
python3 doc_inventory.py examples/contract.json
# JSON status=match, exit 0
python3 -B -m unittest -v
```

A complete contract:

```json
{"version": 1, "root": "docs", "documents": ["index.md", "nested/guide.md"]}
```

`root` is relative to the manifest file, **not the current working directory**. `.` is permitted as the root. Every document is relative to that root, and the list must explicitly include all regular files ending in `.md` (case insensitive). Hidden and nested directories are included. Other regular files are ignored. There is no implicit exclusion for `.git`, generated directories, or private folders: choose a narrow documentation root.

## Contract and output

- Exact fields and integer version 1 are required; duplicate JSON keys and document entries are errors.
- Paths must be canonical relative POSIX strings. Absolute paths, `..`, redundant separators, backslashes, colons, control characters and invalid Unicode are refused. No globs.
- Matching is exact, including case. Case-fold collisions are reported independently, including ancestor directory collisions. This is a conservative portability warning using Python `casefold`, not an emulation of Windows/macOS filename rules or Unicode normalization.
- Empty document lists and empty directories are supported; a missing root is an error, never an empty match.
- All symlinks/reparse points encountered in manifest/root components or beneath the root are refused, including broken links and non-Markdown links. FIFOs/devices/sockets are refused without opening them.
- A scan error or invalid input returns `status=error`, without partial missing/unlisted lists that could be mistaken for a complete result.
- Maximum manifest size is 2 MiB; maximum declared paths and scanned entries are each 100,000. Directory entries count toward the scan cap.

Results are one JSON object on stdout. Sorted keys and lists, no timestamps or absolute root paths on normal results, and no dependence on enumeration or declaration order make successful and mismatch reports deterministic for the same tree. Error text can contain filesystem paths; review reports before sharing. CLI usage errors use argparse's stderr and exit 2 rather than JSON. Normal output:

```json
{"case_collisions": [], "expected_count": 2, "found_count": 2, "missing": [], "schema": "doc-inventory-contract/v1", "status": "match", "unlisted": []}
```

Exit **0** = match, **1** = complete scan with missing/unlisted/case collision, **2** = invalid manifest, incomplete scan or CLI error. Check the exit code before consuming the report. The tool writes only stdout; shell redirection is your explicit output-file operation. Place that file outside the documentation root to avoid introducing an input.

## Boundaries

This checks filenames and topology only: it cannot find empty articles, duplicate frontmatter IDs, broken links, bad content, missing assets or stale prose. It does not compute file hashes or compare historical snapshots. Hardlinks are treated as distinct paths. It is not a linter, build system, Markdown parser, security sandbox, or an atomic filesystem snapshot. Concurrent/adversarial changes can race path checks and enumeration; use an immutable checkout. Windows reparse rejection is defensive, not Windows certification. No network APIs are used, but OS-mounted network filesystems may cause traffic outside the program's control. Reading metadata may update access times.

## Motivation and related work

[GoogleChrome/modern-web-guidance-src issue #3536](https://github.com/GoogleChrome/modern-web-guidance-src/issues/3536) describes a nested guide being omitted from an inventory. That project already has upstream work on its validator; this independent implementation is **not** an upstream fix, does not reuse its code, and does not validate its guide format. Its source repository uses Apache-2.0; no source was copied here.

[Input Tree Digest](https://github.com/Aliciawque/input-tree-digest) hashes declared build inputs and compares snapshots. This tool instead checks a reviewed list against all Markdown paths, detecting unexpected nested documents without reading their bytes. [Clip Log Preflight](https://github.com/Aliciawque/clip-log-preflight) resolves media ranges and editorial scopes, not documentation inventories. Generic build scripts can implement similar checks; no novelty or replacement claim is made.

## Verification

Linux Python 3.12.14: 20 unit tests passed, including real subprocess exit codes, nested/hidden paths, strict JSON/schema faults, Unicode/case rules, symlink and FIFO refusal, injected scan failures, caps and no document-content reads. Fixtures are synthetic. Windows/macOS and other Python versions have not been tested; no hosted CI has run. Published source: https://github.com/Aliciawque/doc-inventory-contract. The documented local checks were rerun on November 14, 2026 to publish the November 13 delivery; no hosted CI has run.

## License

MIT, see [LICENSE](LICENSE).
