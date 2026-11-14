import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import doc_inventory as d


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'docs'
        self.root.mkdir()
        self.manifest = self.base / 'contract.json'

    def config(self, docs, **kw):
        value = {'version': 1, 'root': 'docs', 'documents': docs}
        value.update(kw)
        self.manifest.write_text(json.dumps(value), encoding='utf-8')

    def file(self, name):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('sentinel', encoding='utf-8')

    def test_empty_tree(self):
        self.config([])
        self.assertEqual(d.audit(self.manifest)['status'], 'match')

    def test_missing_root_not_empty(self):
        self.config([], root='absent')
        with self.assertRaises(OSError): d.audit(self.manifest)

    def test_nested_unlisted(self):
        self.config(['guide.md'])
        self.file('guide.md')
        self.file('nested/deep/guide.md')
        self.assertEqual(d.audit(self.manifest)['unlisted'], ['nested/deep/guide.md'])

    def test_missing_and_unlisted(self):
        self.config(['old.md'])
        self.file('new.md')
        r = d.audit(self.manifest)
        self.assertEqual((r['missing'], r['unlisted']), (['old.md'], ['new.md']))

    def test_case_collision(self):
        self.config(['Guide.md'])
        self.file('guide.md')
        self.assertEqual(d.audit(self.manifest)['case_collisions'], [['Guide.md', 'guide.md']])

    def test_ancestor_case_collision(self):
        self.config(['A/x.md', 'a/y.md'])
        self.assertEqual(d.audit(self.manifest)['case_collisions'], [['A', 'a']])

    def test_hidden_and_uppercase(self):
        self.config(['.hidden/note.MD'])
        self.file('.hidden/note.MD')
        self.file('ignored.txt')
        self.assertEqual(d.audit(self.manifest)['status'], 'match')

    def test_document_bytes_not_read(self):
        self.config(['x.md']); self.file('x.md')
        original = Path.open
        def guarded(path, *a, **k):
            self.assertNotEqual(path.suffix, '.md')
            return original(path, *a, **k)
        with patch.object(Path, 'open', guarded):
            self.assertEqual(d.audit(self.manifest)['status'], 'match')

    def test_invalid_paths(self):
        for name in ['../x.md', '/x.md', 'a//x.md', './x.md', 'a/../x.md', 'C:x.md', 'a\\x.md', 'x\n.md']:
            with self.subTest(name=name):
                self.config([name])
                with self.assertRaises(d.ContractError): d.audit(self.manifest)

    def test_invalid_schema(self):
        for kw in [{'version':True}, {'version':1.0}, {'documents':'x.md'}, {'extra':1}, {'root':'../docs'}]:
            self.config([], **kw) if 'documents' not in kw else self.config('x.md')
            with self.assertRaises(d.ContractError): d.audit(self.manifest)

    def test_duplicate_keys(self):
        self.manifest.write_text('{"version":1,"version":1,"root":"docs","documents":[]}')
        with self.assertRaises(d.ContractError): d.audit(self.manifest)

    def test_duplicate_paths(self):
        self.config(['x.md', 'x.md'])
        with self.assertRaises(d.ContractError): d.audit(self.manifest)

    def test_symlink(self):
        self.config([])
        (self.root / 'hidden').symlink_to(self.base / 'absent')
        with self.assertRaises(d.ContractError): d.audit(self.manifest)

    def test_symlink_root(self):
        (self.base / 'alias').symlink_to(self.root, target_is_directory=True)
        self.config([], root='alias')
        with self.assertRaises(d.ContractError): d.audit(self.manifest)

    def test_symlink_manifest(self):
        self.config([])
        alias = self.base / 'alias.json'; alias.symlink_to(self.manifest)
        with self.assertRaises(d.ContractError): d.audit(alias)

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'POSIX FIFO')
    def test_fifo(self):
        self.config([]); os.mkfifo(self.root / 'pipe')
        with self.assertRaises(d.ContractError): d.audit(self.manifest)

    def test_scan_error(self):
        self.config([])
        with patch.object(os, 'scandir', side_effect=PermissionError('fixture')):
            with self.assertRaises(PermissionError): d.audit(self.manifest)

    def test_caps(self):
        self.config([]); self.file('x.md')
        with patch.object(d, 'MAX_ENTRIES', 0):
            with self.assertRaises(d.ContractError): d.audit(self.manifest)
        with patch.object(d, 'MAX_MANIFEST', 2):
            with self.assertRaises(d.ContractError): d.audit(self.manifest)

    def test_unicode_determinism(self):
        self.config(['日本語.md', 'b.md', 'a.md'])
        for name in ['a.md', '日本語.md', 'b.md']: self.file(name)
        first = d.audit(self.manifest)
        self.config(['b.md', 'a.md', '日本語.md'])
        self.assertEqual(first, d.audit(self.manifest))

    def test_cli_codes(self):
        script = str(Path(d.__file__).absolute())
        for docs, code in [([],0), (['missing.md'],1), (['../bad.md'],2)]:
            self.config(docs)
            result = subprocess.run([sys.executable, '-B', script, str(self.manifest)], capture_output=True, text=True)
            self.assertEqual(result.returncode, code, result.stderr)
            self.assertEqual(json.loads(result.stdout)['status'], ['match','mismatch','error'][code])


if __name__ == '__main__': unittest.main()
