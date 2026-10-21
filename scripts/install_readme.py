#!/usr/bin/env python3
"""Patch only the introductory banner and the existing GitHub Stats section."""
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
README=ROOT/'README.md'
HERO='''<p align="center">
  <img src="assets/hero-animated.gif" width="900" alt="Roki pixel-art midnight coding banner" />
</p>'''
STATS='''<p align="center">
  <img src="assets/stats-animated.gif" width="900" alt="Roki's GitHub statistics and last 30 days of activity" />
</p>'''


def modify_readme(readme:str)->str:
    if not re.search(r'(?m)^#\s+.+$',readme):
        raise ValueError('No primary README H1 heading; refusing to modify')
    if 'assets/hero-animated.gif' not in readme:
        readme=re.sub(r'(?m)^(# .+\n)',lambda m:m.group(1)+'\n'+HERO+'\n',readme,count=1)
    if re.search(r'(?m)^## GitHub Stats\s*$',readme):
        # Retain existing HTML comments (for example the WakaTime setup note).
        def replace_section(match):
            comments=re.findall(r'<!--.*?-->',match.group(0),flags=re.S)
            suffix='\n\n'.join(comments)
            return '## GitHub Stats\n\n'+STATS+'\n\n'+(suffix+'\n\n' if suffix else '')
        readme=re.sub(r'(?ms)^## GitHub Stats\s*\n.*?(?=^## |\Z)',replace_section,readme,count=1)
    elif 'assets/stats-animated.gif' not in readme:
        readme += '\n## GitHub Stats\n\n'+STATS+'\n'
    return readme

if __name__=='__main__':
    if not README.exists():
        raise SystemExit('README.md not found: copy package files into Roki0i/Roki0i repository first.')
    old=README.read_text(encoding='utf-8')
    new=modify_readme(old)
    if new!=old:
        README.write_text(new,encoding='utf-8')
        print('README updated; check git diff before pushing.')
    else:
        print('README already contains both animated images.')
