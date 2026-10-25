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
BASE = 'https://majdialomari.com/'
SOCIAL_IMAGE = BASE + 'assets/majdi-portrait-original.jpg'
errors=[];urls=set();count=0;all_titles=set();canonical_by_path={}

for f in [*ROOT.rglob('index.html'),ROOT/'404.html']:
    count+=1;s=Scan();s.feed(f.read_text(encoding='utf8'))
    attrs=s.attrs
    rel=f.relative_to(ROOT).as_posix()
    expected_url=BASE+('' if rel=='index.html' else ('404.html' if rel=='404.html' else rel[:-10]))
    canonical_by_path[rel]=expected_url
    canonical_values=[a.get('href','') for tag,a in attrs if tag=='link' and a.get('rel')=='canonical']
    if canonical_values != [expected_url]:
        errors.append(f'{rel}: expected one canonical {expected_url}, got {canonical_values}')
    og_urls=[a.get('content','') for tag,a in attrs if tag=='meta' and a.get('property')=='og:url']
    if og_urls != [expected_url]:
        errors.append(f'{rel}: Open Graph URL disagrees with canonical: {og_urls}')
    if rel=='404.html':
        if not any(tag=='meta' and a.get('name')=='robots' and 'noindex' in a.get('content','') for tag,a in attrs):
            errors.append('404 is missing noindex')
    else:
        og_images=[a.get('content','') for tag,a in attrs if tag=='meta' and a.get('property')=='og:image']
        if og_images != [SOCIAL_IMAGE]:
            errors.append(f'{rel}: social image should be hosted on the main domain')
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
        try:
            structured=json.loads(blob)
            if rel in ('index.html','profile/index.html') and structured.get('@type')=='Person':
                if structured.get('url')!=BASE or structured.get('@id')!=BASE+'#person':
                    errors.append(f'{rel}: Person metadata is not linked to the primary domain')
        except Exception:errors.append(f'{f}: invalid structured data')
    if f.name=='index.html':
        if s.title in all_titles: errors.append(f'duplicate title {s.title}')
        all_titles.add(s.title)
if (ROOT/'sitemap.xml').exists():
    sitemap=ET.parse(ROOT/'sitemap.xml')
    entries=[x.text for x in sitemap.getroot().iter() if x.tag.endswith('loc')]
    n=len(entries)
    if n!=48:errors.append(f'Expected 48 sitemap routes, got {n}')
    indexed_urls={url for name,url in canonical_by_path.items() if name!='404.html'}
    if len(entries)!=len(set(entries)) or set(entries)!=indexed_urls:
        errors.append('Sitemap URLs must match all and only indexable canonical URLs')
    if any(not (u or '').startswith(BASE) or 'github.io' in (u or '') for u in entries):
        errors.append('Sitemap contains non-primary-domain URLs')
else:errors.append('Missing sitemap.xml')
robots=ROOT/'robots.txt'
if not robots.exists() or f'Sitemap: {BASE}sitemap.xml' not in robots.read_text(encoding='utf8'):
    errors.append('robots.txt must advertise the primary-domain sitemap')

# GitHub Pages serves 404.html at the *missing URL*, so asset/link
# references must not resolve relative to that unknown nested directory.
from urllib.parse import urljoin
home_scan = Scan()
home_scan.feed((ROOT/'index.html').read_text(encoding='utf8'))
base = next((a.get('href') for tag,a in home_scan.attrs
             if tag=='link' and a.get('rel')=='canonical'), '')
if base:
    missing_url = base + 'research/publications/nonexistent/'
    fail_scan = Scan()
    fail_scan.feed((ROOT/'404.html').read_text(encoding='utf8'))
    referenced = {(tag, a.get('href') or a.get('src', ''))
                  for tag, a in fail_scan.attrs if tag in ('a','link','script')}
    for needed in (base+'assets/site.css', base+'assets/site.js',
                   base+'research/', base+'publications/', base+'profile/'):
        if needed not in {urljoin(missing_url, v) for _,v in referenced if v}:
            errors.append(f'404 breaks at nested URL: {needed}')
    for page in ROOT.rglob('index.html'):
        scan = Scan()
        scan.feed(page.read_text(encoding='utf8'))
        rel = page.relative_to(ROOT).as_posix()
        original_url = base + ('' if rel=='index.html' else rel[:-10])
        # The main four navigation destinations must be valid even when loaded
        # as independent pages, with JavaScript disabled.
        source = page.read_text(encoding='utf8')
        import re as _re
        nav = _re.search(r'<nav\b[^>]*class="site-nav"[^>]*>(.*?)</nav>', source, _re.S)
        if not nav:
            errors.append(f'Navigation missing: {rel}')
        else:
            nav_links = _re.findall(r'<a\b[^>]*href="([^"]+)"', nav.group(1))
            resolved = [urljoin(original_url,v) for v in nav_links]
            expected = [base,base+'research/',base+'publications/',base+'profile/']
            if resolved != expected:
                errors.append(f'Navigation broken: {rel}: {resolved}')
for file in ROOT.rglob('*'):
    if file.suffix in ('.docx','.md','.py','.env','.zip') or file.name in ('SOURCE_NOTES.md','README.md'):
        errors.append(f'Unexpected public source: {file.relative_to(ROOT)}')
if errors:
    print('\n'.join(errors[:50]));sys.exit(1)
print(f'Validated {count} HTML pages, {n} indexed URLs, all relative resources and JSON-LD.')
