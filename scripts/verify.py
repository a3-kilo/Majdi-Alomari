#!/usr/bin/env python3
"""Validate a built release before GitHub Pages upload."""
from pathlib import Path
from html.parser import HTMLParser
import json,re,sys,xml.etree.ElementTree as ET
from urllib.parse import urlparse,unquote
ROOT=Path(__file__).resolve().parents[1]/'dist'
class Scan(HTMLParser):
    def __init__(self):super().__init__();self.attrs=[];self.title='';self.in_title=False;self.json=[];self.in_json=False;self.buffer=''
    def handle_starttag(self,tag,attrs):
        a=dict(attrs);self.attrs.append((tag,a))
        if tag=='title':self.in_title=True
        if tag=='script' and a.get('type')=='application/ld+json':self.in_json=True;self.buffer=''
    def handle_data(self,data):
        if self.in_title:self.title+=data
        if self.in_json:self.buffer+=data
    def handle_endtag(self,tag):
        if tag=='title':self.in_title=False
        if tag=='script' and self.in_json:self.in_json=False;self.json.append(self.buffer)
errors=[];urls=set();count=0;all_titles=set()
for f in [*ROOT.rglob('index.html'),ROOT/'404.html']:
    count+=1;s=Scan();s.feed(f.read_text(encoding='utf8'))
    attrs=s.attrs
    for tag,a in attrs:
        for key in ('href','src'):
            value=a.get(key,'')
            if value.startswith(('https:','http:','mailto:','tel:','data:','#','javascript:')) or not value:continue
            p=(f.parent/value.split('#')[0].split('?')[0]).resolve()
            if not p.exists() and not (p/'index.html').exists():errors.append(f'{f.relative_to(ROOT)}: missing {value}')
        if tag=='link' and a.get('rel')=='canonical':
            url=a.get('href','')
            if not url.startswith('https://'):errors.append(f'{f}: invalid canonical')
            if url in urls:errors.append(f'duplicate URL: {url}')
            urls.add(url)
        if tag=='meta' and a.get('name')=='description' and len(a.get('content',''))>185:errors.append(f'{f}: long meta description')
    for blob in s.json:
        try:json.loads(blob)
        except Exception:errors.append(f'{f}: invalid structured data')
    if f.name=='index.html':
        if s.title in all_titles: errors.append(f'duplicate title {s.title}')
        all_titles.add(s.title)
if (ROOT/'sitemap.xml').exists():
    sitemap=ET.parse(ROOT/'sitemap.xml')
    n=sum(1 for x in sitemap.getroot().iter() if x.tag.endswith('loc'))
    if n!=48:errors.append(f'Expected 48 sitemap routes, got {n}')
else:errors.append('Missing sitemap.xml')
for file in ROOT.rglob('*'):
    if file.suffix in ('.docx','.md','.py','.env','.zip') or file.name in ('SOURCE_NOTES.md','README.md'):
        errors.append(f'Unexpected public source: {file.relative_to(ROOT)}')
if errors:
    print('\n'.join(errors[:50]));sys.exit(1)
print(f'Validated {count} HTML pages, {n} indexed URLs, all relative resources and JSON-LD.')
