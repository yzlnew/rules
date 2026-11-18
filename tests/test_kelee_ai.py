import importlib.util
import base64
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/sync_kelee_ai.py'
spec = importlib.util.spec_from_file_location('sync_kelee_ai', SCRIPT)
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


def payload(text):
    return [line[5:-1] for line in text.splitlines() if line.startswith("  - '")]


class ConversionTests(unittest.TestCase):
    def test_normalization_dedup_and_exact_domains(self):
        output, counts, unique = sync.convert('# comment\nDOMAIN, api.example.com\nDOMAIN,api.example.com\nDOMAIN-SUFFIX, example.org\n')
        self.assertEqual(payload(output), ['DOMAIN,api.example.com', 'DOMAIN-SUFFIX,example.org'])
        self.assertEqual(counts['DOMAIN'], 2)
        self.assertEqual(unique, 2)

    def test_and_retains_both_conditions(self):
        rule = 'AND, ((DOMAIN-KEYWORD, antigravity-auto-updater-), (DOMAIN-SUFFIX, run.app))'
        output, _, _ = sync.convert(rule)
        self.assertEqual(payload(output), ['AND,((DOMAIN-KEYWORD,antigravity-auto-updater-),(DOMAIN-SUFFIX,run.app))'])

    def test_ip_versions_and_no_resolve_preserved(self):
        source = 'IP-CIDR,160.79.104.0/23,no-resolve\nIP-CIDR6,2607:6bc0::/48,no-resolve'
        self.assertEqual(payload(sync.convert(source)[0]), source.splitlines())

    def test_unknown_and_malformed_rules_fail(self):
        for source in ('', '<html>403 Forbidden</html>', 'DOMAIN,example.com,PROXY',
                       'DOMAIN-SUFFIX,*.example.com', 'DOMAIN,example.com # inline',
                       'OR,((DOMAIN,a.com),(DOMAIN,b.com))',
                       'AND,((DOMAIN-KEYWORD,x),(DOMAIN-SUFFIX,com)),PROXY',
                       'IP-CIDR,2607:6bc0::/48', 'IP-CIDR6,160.79.104.0/23',
                       'IP-CIDR,160.79.104.1/23,no-resolve',
                       'IP-CIDR6,2607:6bc0::/48,resolve'):
            with self.subTest(source=source), self.assertRaises(ValueError):
                sync.convert(source)

    def test_invalid_source_does_not_overwrite_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / 'source', Path(tmp) / 'output'
            source.write_text('DOMAIN,example.com\nUNSUPPORTED,something')
            output.write_text('previous snapshot')
            result = subprocess.run([sys.executable, str(SCRIPT), '--source', str(source), '--output', str(output)], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output.read_text(), 'previous snapshot')

    def test_ini_marker_errors_fail(self):
        output = sync.convert('DOMAIN,example.com')[0]
        for ini in ('no AI anchor', sync.BEGIN, sync.END, sync.END + '\n' + sync.BEGIN):
            with self.subTest(ini=ini), self.assertRaises(ValueError):
                sync.update_ini(ini, output)

    def test_check_is_read_only_and_detects_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / 'source', Path(tmp) / 'output'
            source.write_text('DOMAIN,example.com')
            command = [sys.executable, str(SCRIPT), '--source', str(source), '--output', str(output)]
            subprocess.run(command, check=True, capture_output=True)
            self.assertEqual(subprocess.run(command + ['--check'], capture_output=True).returncode, 0)
            output.write_text('drift')
            self.assertEqual(subprocess.run(command + ['--check'], capture_output=True).returncode, 1)
            self.assertEqual(output.read_text(), 'drift')


class IntegrationTests(unittest.TestCase):
    def test_acl_position_and_existing_ai_coverage(self):
        acl = (ROOT / 'ACL_mini.kelee-mihomo.ini.example').read_text()
        self.assertEqual(acl.count('[]RULE-SET,kelee-ai'), 1)
        self.assertEqual(acl.count('ruleset=💬 人工智能,clash-domain:'), 8)
        self.assertLess(acl.index('/ruleset/direct.list'), acl.index('[]RULE-SET,kelee-ai'))
        self.assertLess(acl.index('[]RULE-SET,kelee-ai'), acl.index('clash-domain:'))
        self.assertLess(acl.index('[]RULE-SET,kelee-ai'), acl.index('[]GEOIP,CN'))
        self.assertIn('custom_proxy_group=💬 人工智能`select`', acl)
        # Model the upstream inline path: split pattern and insert group as field 3.
        inline = re.search(r'ruleset=([^,]+),\[\](RULE-SET,kelee-ai)', acl)
        kind, name = inline.group(2).split(',')
        self.assertEqual(f'{kind},{name},{inline.group(1)}', 'RULE-SET,kelee-ai,💬 人工智能')

    def test_default_acl_embeds_all_compatible_rules_without_provider(self):
        default = (ROOT / 'ACL_mini.ini').read_text()
        self.assertNotIn('[]RULE-SET,kelee-ai', default)
        self.assertEqual(default.count('ruleset=💬 人工智能,clash-domain:'), 8)
        data_line = next(line for line in default.splitlines() if line.startswith('ruleset=💬 人工智能,data:'))
        encoded, interval = data_line.split(';base64,', 1)[1].rsplit(',', 1)
        self.assertEqual(interval, '86400')
        rules = base64.b64decode(encoded, altchars=b'-_', validate=True).decode().splitlines()
        full = (ROOT / 'ruleset/kelee-ai.yaml').read_text()
        self.assertEqual(rules, sync.compatible_rules(full))
        self.assertEqual(len(rules), 240)
        self.assertFalse(any(rule.startswith('AND,') for rule in rules))
        self.assertIn('IP-CIDR6,2607:6bc0::/48,no-resolve', rules)
        self.assertLess(default.index('/ruleset/direct.list'), default.index(data_line))
        self.assertLess(default.index(data_line), default.index('clash-domain:'))
        self.assertEqual(sync.update_ini(default, full), default)
        # Removing only the generated block reconstructs the original default INI.
        start = default.index(sync.BEGIN)
        end = default.index(sync.END) + len(sync.END) + 1
        restored = default[:start] + default[end:]
        restored = re.sub(r'; BEGIN KELEE DEV REVIEWED\n.*?; END KELEE DEV REVIEWED\n', '', restored, flags=re.S)
        experiment = (ROOT / 'ACL_mini.kelee-mihomo.ini.example').read_text()
        restored_experiment = ''.join(line for line in experiment.splitlines(keepends=True) if not (
            line.startswith('; 未启用实验方案：') or line.startswith('; Kelee 原生') or
            line.startswith('; 勿改为 clash-domain/') or line == 'ruleset=💬 人工智能,[]RULE-SET,kelee-ai\n'))
        self.assertEqual(restored, restored_experiment)

    def test_reviewed_development_subset_and_priority(self):
        acl = (ROOT / 'ACL_mini.ini').read_text()
        match = re.search(r'; BEGIN KELEE DEV REVIEWED\n(.*?); END KELEE DEV REVIEWED', acl, re.S)
        self.assertIsNotNone(match)
        rules = [line for line in match[1].splitlines() if line.startswith('ruleset=')]
        self.assertEqual(rules, ['ruleset=🚀 节点选择,[]DOMAIN-SUFFIX,' + domain
                                for domain in ('dependabot.com', 'ghcr.io', 'repo.new')])
        self.assertLess(acl.index('clash-domain:'), match.start())
        self.assertLess(acl.index('/ruleset/direct.list'), match.start())
        self.assertLess(match.end(), acl.index('/Clash/ProxyGFWlist.list'))
        self.assertLess(sum(line.startswith('ruleset=') for line in acl.splitlines()), 64)

    def test_shared_platform_intersections_and_boundaries(self):
        rules = payload((ROOT / 'ruleset/kelee-ai.yaml').read_text())
        logical = [sync.AND.fullmatch(rule) for rule in rules if rule.startswith('AND,')]
        self.assertEqual(len(logical), 3)
        for match in logical:
            keyword, suffix = match.groups()
            def matches(host):
                return keyword in host and (host == suffix or host.endswith('.' + suffix))
            self.assertTrue(matches(keyword + '123.' + suffix))
            self.assertTrue(matches('nested.' + keyword + '123.' + suffix))
            self.assertFalse(matches('ordinary.' + suffix))
            self.assertFalse(matches(keyword + '123.unrelated.example'))
            self.assertFalse(matches(keyword + '123.' + suffix + '.evil.example'))
            self.assertFalse(matches(keyword + '123.not' + suffix))
            self.assertNotIn('DOMAIN-SUFFIX,' + suffix, rules)
        self.assertIn('IP-CIDR6,2607:6bc0::/48,no-resolve', rules)

    def test_provider_reference_is_local_and_classical(self):
        fragment = (ROOT / 'ruleset/kelee-ai-provider.yaml').read_text()
        for expected in ('  kelee-ai:', 'type: file', 'behavior: classical', 'format: yaml',
                         'path: ./ruleset/kelee-ai.yaml'):
            self.assertIn(expected, fragment)


if __name__ == '__main__':
    unittest.main()
