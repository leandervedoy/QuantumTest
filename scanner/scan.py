"""Dependency-free, read-only heuristic source scanner. Never executes target code."""
import argparse
import fnmatch
import json
import os
from pathlib import Path
import re
import stat
import sys
from urllib.parse import quote

RULES = [
    ('QT001', 'high', r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', 'Possible private key. Remove it and rotate the key.'),
    ('QT002', 'high', r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|AKIA[A-Z0-9]{16})\b', 'Possible access credential. Remove and rotate it.'),
    ('QT003', 'high', r'''(?i)\b(?:api_key|api_secret|password|access_token)\s*[:=]\s*["'][^"'\s]{12,}["']''', 'Possible hardcoded secret. Review and use a secret store.'),
    ('QT004', 'medium', r'\beval\s*\(', 'Dynamic evaluation. Review whether untrusted input can reach this call.'),
    ('QT005', 'medium', r'\.innerHTML\s*=|dangerouslySetInnerHTML', 'HTML injection sink. Review input sanitization.'),
    ('QT006', 'high', r'(?i)\bverify\s*=\s*False\b|rejectUnauthorized\s*:\s*false\b', 'TLS verification appears disabled. Enable certificate validation.'),
    ('QT007', 'medium', r'\bshell\s*=\s*True\b|\bos\.system\s*\(', 'Shell execution. Review command construction and input handling.'),
    ('QT008', 'medium', r'\bpickle\.loads?\s*\(|\byaml\.load\s*\(', 'Deserialization call. Review trust boundary and safe loader use.'),
]
COMPILED = [(i, s, re.compile(p), m) for i, s, p, m in RULES]
EXCLUDED = {'.git', 'node_modules', '.venv', 'venv', '__pycache__', 'dist', 'build', 'coverage'}
EXTENSIONS = {'.py', '.js', '.jsx', '.ts', '.tsx', '.vue', '.svelte', '.json', '.yaml', '.yml', '.env', '.pem', '.key', '.txt', '.sh', '.html', '.vs'}
LEVELS = {'low': 0, 'medium': 1, 'high': 2, 'none': 3}
MAX_FILES = 10000
MAX_TOTAL_BYTES = 128 * 1048576
MAX_FINDINGS = 5000
MAX_REPORT_BYTES = 9 * 1048576
# Filenames are untrusted input too. Never serialize paths that resemble credentials.
SENSITIVE_PATH = re.compile(
    r'(?i)(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}'
    r'|AKIA[A-Z0-9]{16}|(?:api[_-]?key|api[_-]?secret|password|secret|token|credential)\s*[:=]'
    r'|[A-Za-z0-9_-]{48,})'
)


def safe_path(relative):
    return not SENSITIVE_PATH.search(relative) and not any(ord(char) < 32 for char in relative)


def scan(root, excludes=(), max_bytes=1048576, max_files=MAX_FILES,
         max_total_bytes=MAX_TOTAL_BYTES, max_findings=MAX_FINDINGS):
    if Path(root).is_symlink():
        raise ValueError('Scan path cannot be a symlink')
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError('Scan path must be a directory')
    findings, skipped, scanned, considered, total_bytes = [], [], 0, 0, 0
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED
                         and not (Path(directory) / d).is_symlink()
                         and safe_path((Path(directory) / d).relative_to(root).as_posix()))
        for name in sorted(files):
            path = Path(directory) / name
            relative = path.relative_to(root).as_posix()
            if any(fnmatch.fnmatch(relative, p) for p in excludes):
                continue
            if path.suffix not in EXTENSIONS and not name.startswith('.env'):
                continue
            considered += 1
            if considered > max_files:
                raise ValueError('Scan file limit exceeded')
            if not safe_path(relative):
                skipped.append({'reason': 'sensitive or unsafe path (path withheld)'})
                continue
            try:
                if path.is_symlink():
                    skipped.append({'path': relative, 'reason': 'symlink'})
                    continue
                fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
                with os.fdopen(fd, 'rb') as stream:
                    if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                        skipped.append({'path': relative, 'reason': 'non-regular file'})
                        continue
                    data = stream.read(max_bytes + 1)
                total_bytes += len(data)
                if total_bytes > max_total_bytes:
                    raise ValueError('Scan byte limit exceeded')
                if len(data) > max_bytes or b'\0' in data:
                    skipped.append({'path': relative, 'reason': 'oversized or binary'})
                    continue
                source = data.decode('utf-8')
            except (OSError, UnicodeError):
                skipped.append({'path': relative, 'reason': 'unreadable or non-UTF-8'})
                continue
            scanned += 1
            for number, line in enumerate(source.splitlines(), 1):
                for rule, severity, pattern, message in COMPILED:
                    if pattern.search(line):
                        if len(findings) >= max_findings:
                            raise ValueError('Scan finding limit exceeded')
                        findings.append({'rule': rule, 'severity': severity, 'path': relative, 'line': number, 'message': message})
    return {'tool': 'Vedoy Code Scanner', 'version': '0.1.0', 'scanned_files': scanned, 'skipped': skipped, 'findings': findings}


def sarif(report):
    return {'version': '2.1.0', '$schema': 'https://json.schemastore.org/sarif-2.1.0.json', 'runs': [{
        'tool': {'driver': {'name': report['tool'], 'version': report['version'], 'rules': [
            {'id': i, 'shortDescription': {'text': m}} for i, _, _, m in RULES]}},
        'results': [{'ruleId': f['rule'], 'level': 'error' if f['severity'] == 'high' else 'warning',
                     'message': {'text': f['message']}, 'locations': [{'physicalLocation': {
                         'artifactLocation': {'uri': quote(f['path'], safe='/')},
                         'region': {'startLine': f['line']}}}]} for f in report['findings']]}]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', nargs='?', default='.')
    parser.add_argument('--format', choices=['json', 'sarif'], default='json')
    parser.add_argument('--output', help='Report file; defaults to stdout')
    parser.add_argument('--exclude', action='append', default=[], help='Repeatable root-relative glob')
    parser.add_argument('--fail-on', choices=LEVELS, default='high')
    args = parser.parse_args(argv)
    try:
        excludes = list(args.exclude)
        if args.output:
            try:
                excludes.append(Path(args.output).resolve().relative_to(Path(args.path).resolve()).as_posix())
            except ValueError:
                pass
        report = scan(args.path, excludes)
        result = json.dumps(sarif(report) if args.format == 'sarif' else report, indent=2) + '\n'
        if len(result.encode('utf-8')) > MAX_REPORT_BYTES:
            raise ValueError('Report size limit exceeded')
        if args.output:
            Path(args.output).write_text(result, encoding='utf-8')
        else:
            print(result, end='')
        return int(any(LEVELS[f['severity']] >= LEVELS[args.fail_on] for f in report['findings']))
    except (OSError, ValueError):
        print('Scan failed: check the input path, permissions and scan limits.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
