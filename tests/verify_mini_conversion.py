#!/usr/bin/env python3
"""Offline real-converter + Mihomo config check, using only synthetic node data."""
import argparse
import base64
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


def verify(repo, converter, mihomo, country, output):
    output.mkdir(parents=True, exist_ok=True)
    binary = output / 'subconverter'
    shutil.copy2(converter, binary)
    (output / 'base').mkdir(exist_ok=True)
    (output / 'templates').mkdir(exist_ok=True)
    shutil.copyfile(converter.parent / 'base/all_base.tpl', output / 'base/all_base.tpl')
    ini = (repo / 'ACL_mini.ini').read_text()
    transformed, remote_count = [], 0
    for number, line in enumerate(ini.splitlines()):
        if line.startswith('ruleset=') and ',[]' not in line and ',data:' not in line:
            group, url = line[len('ruleset='):].split(',', 1)
            fixture = f'fixture-{number}.list'
            if url.startswith('https://raw.githubusercontent.com/yzlnew/rules/main/ruleset/'):
                name = url.rsplit('/', 1)[1]
                content = (repo / 'ruleset' / name).read_text()
            elif url.startswith('clash-domain:'):
                remote_count += 1
                fixture = f'fixture-{number}.yaml'
                content = f"payload:\n  - 'ai-fixture-{number}.example.org'\n"
            else:
                content = f'DOMAIN,fixture-{number}.example.org\n'
            (output / fixture).write_text(content)
            prefix = 'clash-domain:' if url.startswith('clash-domain:') else ''
            line = f'ruleset={group},{prefix}{fixture}'
        transformed.append(line)
    assert remote_count == 8, 'all eight original AI sources must remain'
    (output / 'external.ini').write_text('\n'.join(transformed) + '\n')
    (output / 'pref.ini').write_text('''[common]
api_mode=false
clash_rule_base=base/all_base.tpl
[template]
clash.allow_lan=false
[node_pref]
clash_use_new_field_name=true
''')
    (output / 'generate.ini').write_text('''[mini]
path=generated.yaml
target=clash
url=ss://YWVzLTEyOC1nY206c3ludGhldGljLXBhc3N3b3Jk@192.0.2.1:1080#Synthetic
config=external.ini
''')
    run = subprocess.run([str(binary), '-g', '-f', str(output / 'pref.ini'), '--artifact', 'mini'],
                         cwd=output, capture_output=True, text=True, timeout=45)
    (output / 'converter.log').write_text(run.stdout + run.stderr)
    assert run.returncode == 0, 'converter failed: ' + str(output / 'converter.log')
    assert '[ERRO]' not in run.stderr and '[WARN]' not in run.stderr, 'inspect converter.log'
    generated = (output / 'generated.yaml').read_text()
    # Official generator emits plain block scalars for these validated rule grammars.
    rules = [line[4:] for line in generated.split('rules:\n', 1)[1].splitlines() if line.startswith('  - ')]
    data = next(line for line in ini.splitlines() if line.startswith('ruleset=💬 人工智能,data:'))
    encoded = data.split(';base64,', 1)[1].rsplit(',', 1)[0]
    source_rules = base64.b64decode(encoded, altchars=b'-_', validate=True).decode().splitlines()
    expected = []
    for rule in source_rules:
        parts = rule.split(',')
        expected.append(','.join(parts[:2] + ['💬 人工智能'] + parts[2:]))
    assert len(expected) == 240
    assert [r for r in rules if r in expected] == expected
    assert all(rules.count(r) == 1 for r in expected)
    dev = ['DOMAIN-SUFFIX,' + d + ',🚀 节点选择' for d in ('dependabot.com', 'ghcr.io', 'repo.new')]
    assert all(rules.count(r) == 1 for r in dev)
    assert not any(r.startswith(('AND,', 'RULE-SET,')) for r in rules)
    assert rules.index('DOMAIN-KEYWORD,aliyun,🎯 全球直连') < rules.index(expected[0])
    ai_fixtures = [r for r in rules if r.startswith('DOMAIN,ai-fixture-')]
    assert len(ai_fixtures) == 8
    assert rules.index(expected[-1]) < rules.index(ai_fixtures[0]) < rules.index(dev[0])
    assert rules[-1] == 'MATCH,🐟 漏网之鱼'
    for group in re.findall(r'^custom_proxy_group=([^`]+)', ini, re.M):
        assert group in generated
    home = output / 'mihomo-home'
    home.mkdir(exist_ok=True)
    shutil.copyfile(country, home / 'country.mmdb')
    checked = subprocess.run([str(mihomo), '-t', '-d', str(home), '-f', str(output / 'generated.yaml')],
                             capture_output=True, text=True, timeout=30)
    (output / 'mihomo.log').write_text(checked.stdout + checked.stderr)
    assert checked.returncode == 0, 'Mihomo config check failed: ' + str(output / 'mihomo.log')
    print('PASS: real subconverter output has all 240 AI + 3 reviewed dev rules, eight AI sources, correct priority/policies, IPv6/no-resolve; Mihomo -t passed')
    print('Evidence:', output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--converter', required=True, type=Path)
    parser.add_argument('--mihomo', required=True, type=Path)
    parser.add_argument('--country-mmdb', required=True, type=Path)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path, help='new directory for logs and generated config')
    args = parser.parse_args()
    output = args.output.resolve() if args.output else Path(tempfile.mkdtemp(prefix='kelee-mini-verify-'))
    if args.output and output.exists():
        parser.error('--output must be a new directory')
    verify(args.repo.resolve(), args.converter.resolve(), args.mihomo.resolve(), args.country_mmdb.resolve(), output)


if __name__ == '__main__':
    main()
