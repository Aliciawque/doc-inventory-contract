"""Explicit documentation inventory contracts; no document content reads."""
import argparse
import json
import os
from pathlib import Path
import stat
import sys

MAX_MANIFEST = 2 * 1024 * 1024
MAX_ENTRIES = 100000


class ContractError(ValueError):
    pass


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ContractError('duplicate JSON key: ' + key)
        result[key] = value
    return result


def relative(value, allow_dot=False):
    if not isinstance(value, str) or not value or '\\' in value or ':' in value:
        raise ContractError('paths must be canonical relative POSIX strings')
    if any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in value):
        raise ContractError('control characters or invalid Unicode in path')
    if value == '.' and allow_dot:
        return value
    if any(part in ('', '.', '..') for part in value.split('/')):
        raise ContractError('noncanonical or escaping path: ' + value)
    return value


def checked(path, directory=False):
    """Reject symbolic links and Windows reparse points in every component."""
    path = Path(os.path.abspath(path))
    for component in list(reversed(path.parents)) + [path]:
        info = component.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ContractError('linked or reparse path: ' + str(component))
    if directory and not stat.S_ISDIR(info.st_mode):
        raise ContractError('root is not a directory')
    if not directory and not stat.S_ISREG(info.st_mode):
        raise ContractError('manifest is not a regular file')
    return path


def load_manifest(path):
    path = checked(path)
    with path.open('rb') as stream:
        data = stream.read(MAX_MANIFEST + 1)
    if len(data) > MAX_MANIFEST:
        raise ContractError('manifest exceeds 2 MiB')
    config = json.loads(data.decode('utf-8'), object_pairs_hook=unique_object)
    if not isinstance(config, dict) or set(config) != {'version', 'root', 'documents'}:
        raise ContractError('expected exactly version, root and documents')
    if type(config['version']) is not int or config['version'] != 1:
        raise ContractError('version must be integer 1')
    relative(config['root'], allow_dot=True)
    docs = config['documents']
    if not isinstance(docs, list) or len(docs) > MAX_ENTRIES:
        raise ContractError('documents must be a list with at most 100000 entries')
    for doc in docs:
        relative(doc)
        if not doc.lower().endswith('.md'):
            raise ContractError('documents must end with .md (case insensitive)')
    if len(docs) != len(set(docs)):
        raise ContractError('duplicate document declaration')
    return path.parent / config['root'], set(docs)


def collisions(paths):
    # Check ancestor components too: A/a directories can collide across platforms.
    groups = {}
    for path in paths:
        parts = path.split('/')
        for i in range(1, len(parts) + 1):
            prefix = '/'.join(parts[:i])
            groups.setdefault(prefix.casefold(), set()).add(prefix)
    return sorted(sorted(group) for group in groups.values() if len(group) > 1)


def audit(manifest):
    root, expected = load_manifest(manifest)
    root = checked(root, directory=True)
    found = set()
    stack = [root]
    count = 0
    while stack:
        directory = stack.pop()
        with os.scandir(directory) as iterator:
            for entry in iterator:
                count += 1
                if count > MAX_ENTRIES:
                    raise ContractError('scan exceeds 100000 entries')
                info = entry.stat(follow_symlinks=False)
                if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                    raise ContractError('linked or reparse entry: ' + str(Path(entry.path).relative_to(root)))
                if stat.S_ISDIR(info.st_mode):
                    stack.append(Path(entry.path))
                elif stat.S_ISREG(info.st_mode):
                    if entry.name.lower().endswith('.md'):
                        doc = Path(entry.path).relative_to(root).as_posix()
                        relative(doc)
                        found.add(doc)
                else:
                    raise ContractError('unsupported filesystem entry')
    missing = sorted(expected - found)
    unlisted = sorted(found - expected)
    case_collisions = collisions(expected | found)
    return {'schema': 'doc-inventory-contract/v1', 'status': 'mismatch' if missing or unlisted or case_collisions else 'match',
            'missing': missing, 'unlisted': unlisted, 'case_collisions': case_collisions,
            'expected_count': len(expected), 'found_count': len(found)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest')
    args = parser.parse_args(argv)
    try:
        result = audit(args.manifest)
        code = 0 if result['status'] == 'match' else 1
    except (OSError, ValueError, UnicodeError, RecursionError) as error:
        result = {'schema': 'doc-inventory-contract/v1', 'status': 'error', 'error': str(error)}
        code = 2
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return code


if __name__ == '__main__':
    sys.exit(main())
