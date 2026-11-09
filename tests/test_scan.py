import json
from pathlib import Path
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


if __name__ == '__main__':
    unittest.main()
