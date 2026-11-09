import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from scanner.scan import main, sarif, scan


class ScannerTests(unittest.TestCase):
    def test_rules_and_redaction(self):
        samples = ['-----BEGIN PRIVATE KEY-----', 'ghp_' + 'a' * 36,
                   'password = "verysecretvalue"', 'eval(input)', 'el.innerHTML = input',
                   'verify=False', 'os.system(command)', 'pickle.loads(data)']
        with tempfile.TemporaryDirectory() as d:
            Path(d, 'app.py').write_text('\n'.join(samples))
            report = scan(d)
            self.assertEqual({f['rule'] for f in report['findings']}, {f'QT00{i}' for i in range(1, 9)})
            self.assertNotIn('verysecretvalue', json.dumps(report))
            self.assertEqual(sarif(report)['version'], '2.1.0')
            self.assertEqual(report['findings'][0]['line'], 1)

    def test_skips_and_excludes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'node_modules').mkdir()
            (root / 'node_modules/a.js').write_text('eval(x)')
            (root / 'binary.py').write_bytes(b'\0eval(x)')
            (root / 'big.py').write_text('x' * 100)
            (root / 'skip.py').write_text('eval(x)')
            (root / 'link.py').symlink_to('/etc/passwd')
            report = scan(d, ['skip.py'], max_bytes=50)
            self.assertEqual(report['findings'], [])
            self.assertEqual(len(report['skipped']), 3)

    def test_cli_threshold_and_invalid_path(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, 'app.js').write_text('eval(x)')
            out = str(Path(d, 'report.json'))
            self.assertEqual(main([d, '--output', out]), 0)
            self.assertEqual(main([d, '--output', out, '--fail-on', 'medium']), 1)
            self.assertEqual(main([d, '--output', out, '--fail-on', 'none']), 0)
            self.assertEqual(main([d + '/missing']), 2)

    def test_sensitive_paths_and_errors_never_reach_reports_or_logs(self):
        marker = 'synthetic-secret-0123456789ABCDEF'
        with tempfile.TemporaryDirectory() as d:
            root = Path(d, 'source')
            root.mkdir()
            (root / 'app.js').write_text('const password = "' + marker + '";\neval(input);')
            (root / ('api_key=' + marker + '.js')).write_text('eval(input)')
            (root / ('token=' + marker)).mkdir()
            (root / ('token=' + marker) / 'app.js').write_text('eval(input)')
            report = scan(root)
            self.assertNotIn(marker, json.dumps(report))
            self.assertNotIn(marker, json.dumps(sarif(report)))
            self.assertEqual(len(report['findings']), 2)
            self.assertTrue(any('path withheld' in item['reason'] for item in report['skipped']))
            run = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / 'scanner' / 'scan.py'),
                                  str(root / marker)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 2)
            self.assertNotIn(marker, run.stdout + run.stderr)

    def test_symlinks_and_global_limits(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d, 'source')
            root.mkdir()
            outside = Path(d, 'outside.js')
            outside.write_text('eval(input)')
            (root / 'link.js').symlink_to(outside)
            (root / 'a.js').write_text('eval(input)')
            (root / 'b.js').write_text('eval(input)')
            self.assertEqual([f['path'] for f in scan(root)['findings']], ['a.js', 'b.js'])
            with self.assertRaisesRegex(ValueError, 'file limit'):
                scan(root, max_files=2)
            with self.assertRaisesRegex(ValueError, 'byte limit'):
                scan(root, max_total_bytes=4)
            with self.assertRaisesRegex(ValueError, 'finding limit'):
                scan(root, max_findings=1)
            linked = Path(d, 'linked-root')
            linked.symlink_to(root, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'symlink'):
                scan(linked)


if __name__ == '__main__':
    unittest.main()
