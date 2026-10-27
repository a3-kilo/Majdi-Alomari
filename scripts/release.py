#!/usr/bin/env python3
"""Prepare the public, static GitHub Pages artifact from the editable site folder."""
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape
import argparse, html, json, os, re, shutil

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'site'
DEST = ROOT / 'dist'
ORIGINALS = {
    'portrait': ('https://i.ibb.co/KJ2XkbP/Majdi-Alomari-Photo-1.jpg', 'majdi-portrait-original.jpg', b'\xff\xd8\xff'),
    'university': ('https://edugate.au.edu.kw/au/resources/barcelona-layout/images/ack.webp', 'au-official-logo.webp', b'RIFF'),
    'kfas': ('https://www.kfas.org.kw/image/logo_c.png', 'kfas-official-logo.png', b'\x89PNG\r\n\x1a\n'),
}


PRIMARY_DOMAIN = 'majdialomari.com'


def get_public_base():
    """Only publish the verified public domain, never an incidental GitHub URL."""
    cname = SITE / 'CNAME'
    if not cname.is_file():
        raise SystemExit('Missing site/CNAME. Refusing to publish a GitHub-based sitemap.')
    domain = cname.read_text(encoding='utf8').strip().lower()
    if domain != PRIMARY_DOMAIN:
        raise SystemExit(
            f'site/CNAME must contain {PRIMARY_DOMAIN!r}, not {domain!r}. '
            'Production SEO URLs must use the public domain.'
        )
    return f'https://{PRIMARY_DOMAIN}/'


def obtain(source, dest, magic, strict):
    if dest.exists() and dest.stat().st_size > 1000 and dest.read_bytes().startswith(magic):
        return
    req = Request(source, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'image/*'})
    try:
        with urlopen(req, timeout=25) as response:
            data = response.read(14_000_000)
        if len(data) < 1000 or not data.startswith(magic):
            raise ValueError('Incorrect image type or empty asset')
        dest.write_bytes(data)
    except Exception as error:
        if strict:
            raise SystemExit(f'Could not fetch {dest.name}. Add the approved original image to site/assets/ and deploy again. Error: {error}')
        print(f'Asset not locally available for preview: {dest.name}')
        return


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--preview', action='store_true', help='Prepare local preview without downloading assets or canonical URLs')
    args = parser.parse_args()
    if DEST.exists():
        shutil.rmtree(DEST)
    shutil.copytree(SITE, DEST)
    base = None if args.preview else get_public_base()
    if not args.preview and not base:
        raise SystemExit('Missing site/CNAME for the production domain.')
    for name, (url, filename, magic) in ORIGINALS.items():
        original = SITE / 'assets' / filename
        target = DEST / 'assets' / filename
        if original.exists():
            shutil.copy2(original, target)
        if not args.preview:
            obtain(url, target, magic, strict=True)
    for page in [*DEST.rglob('index.html'), DEST/'404.html']:
        rel = page.relative_to(DEST).as_posix()
        depth = max(len(page.relative_to(DEST).parts)-1, 0)
        prefix = '../' * depth
        body = page.read_text(encoding='utf8')
        if not args.preview:
            for _, (external, filename, _) in ORIGINALS.items():
                body = body.replace(external, prefix+'assets/'+filename)
        if base:
            page_uri = '' if rel=='index.html' else ('404.html' if rel=='404.html' else rel[:-10])
            url = base + page_uri
            body = re.sub(r'\s*<link\b[^>]*rel="canonical"[^>]*>', '', body)
            body = re.sub(r'\s*<meta\b[^>]*property="og:url"[^>]*>', '', body)
            seo = (f'\n    <link rel="canonical" href="{html.escape(url,quote=True)}"/>'
                   f'\n    <meta property="og:url" content="{html.escape(url,quote=True)}"/>')
            if rel=='404.html':
                # GitHub serves this page at whatever missing URL was requested.
                # Absolute site URLs keep its CSS, script, icons and navigation
                # working even several folders deep.
                def rebase_404_link(match):
                    value = html.unescape(match.group(3))
                    if value.startswith(('#', 'http:', 'https:', 'mailto:', 'tel:', 'data:')):
                        return match.group(0)
                    absolute = urljoin(base, value)
                    return match.group(1) + match.group(2) + '="' + html.escape(absolute, quote=True) + '"' + match.group(4)
                body = re.sub(r'(<(?:a|link|script)\b[^>]*?\s)(href|src)="([^"]*)"([^>]*>)',
                              rebase_404_link, body, flags=re.I)
            if rel == 'index.html':
                # One coherent, domain-level site name (not keyword variants).
                website = {
                    '@context': 'https://schema.org',
                    '@type': 'WebSite',
                    '@id': base + '#website',
                    'url': base,
                    'name': 'Dr. Majdi M. Alomari',
                    'alternateName': 'Majdi Alomari',
                    'inLanguage': 'en',
                    'about': {'@id': base + '#person'},
                }
                seo += ('\n    <script type="application/ld+json">'
                        + json.dumps(website, ensure_ascii=False, separators=(',', ':'))
                        + '</script>')

            # Associate the homepage, Profile and each publication with the
            # same academic identity, without editing visible text or titles.
            person_id = base + '#person'

            def connect_identity(match):
                payload = json.loads(html.unescape(match.group(2)))
                kind = payload.get('@type')

                def person_identity(person):
                    if not isinstance(person, dict) or person.get('@type') != 'Person':
                        return
                    if person.get('name') != 'Majdi M. Alomari':
                        return
                    person['@id'] = person_id
                    person['url'] = base
                    person['alternateName'] = ['Majdi Alomari', 'Dr. Majdi Alomari']
                    person['image'] = base + 'assets/majdi-portrait-original.jpg'

                if kind == 'Person':
                    person_identity(payload)
                elif kind == 'ProfilePage' and rel == 'profile/index.html':
                    payload['@id'] = url + '#webpage'
                    payload['url'] = url
                    payload['isPartOf'] = {'@id': base + '#website'}
                    person_identity(payload.get('mainEntity'))
                elif kind in ('ScholarlyArticle', 'Chapter', 'Book') and rel.startswith('papers/'):
                    payload['@id'] = url + '#publication'
                    payload['url'] = url
                    payload['mainEntityOfPage'] = {'@id': url}
                    authors = payload.get('author', [])
                    if isinstance(authors, dict):
                        authors = [authors]
                    for author in authors:
                        if isinstance(author, dict) and author.get('@type') == 'Person' and author.get('name') == 'Majdi M. Alomari':
                            author['@id'] = person_id
                else:
                    return match.group(0)
                return (match.group(1) + '\n'
                        + json.dumps(payload, ensure_ascii=False, indent=2)
                        + '\n' + match.group(3))

            body = re.sub(
                r'(<script type="application/ld\+json">)(.*?)(</script>)',
                connect_identity, body, flags=re.S,
            )
            body = body.replace('</head>', seo + '\n  </head>', 1)
            # WhatsApp, LinkedIn and other crawlers need an absolute public image
            # URL. A file:// or a relative image URL will not appear in previews.
            photo_url = base + 'assets/majdi-portrait-original.jpg'
            body = re.sub(
                r'(<meta\b[^>]*\bproperty="og:image"[^>]*\bcontent=")[^"]*(")',
                lambda m: m.group(1) + html.escape(photo_url, quote=True) + m.group(2), body
            )
            body = re.sub(
                r'(<meta\b[^>]*\bcontent=")[^"]*("[^>]*\bproperty="og:image"[^>]*>)',
                lambda m: m.group(1) + html.escape(photo_url, quote=True) + m.group(2), body
            )
            # Add explicit image details for social scrapers. They appear only in
            # the head and don't change the displayed page.
            social = ('\n    <meta property="og:image:secure_url" content="' + html.escape(photo_url, quote=True) + '"/>'
                      '\n    <meta property="og:image:type" content="image/jpeg"/>'
                      '\n    <meta name="twitter:image" content="' + html.escape(photo_url, quote=True) + '"/>'
                      '\n    <meta name="twitter:image:alt" content="Dr. Majdi M. Alomari"/>')
            body = body.replace('</head>', social + '\n  </head>', 1)
        page.write_text(body,encoding='utf8')
    js = DEST/'assets/site.js'
    js_text = js.read_text(encoding='utf8')
    if not args.preview:
        # The browser always loads its photo relative to the site.js location,
        # without a remote request or a change in image identity between pages.
        pass
    js.write_text(js_text,encoding='utf8')
    if base:
        paths = sorted(p.relative_to(DEST).as_posix() for p in DEST.rglob('index.html'))
        urls = [base+('' if p=='index.html' else p[:-10]) for p in paths]
        (DEST/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join('<url><loc>'+escape(u)+'</loc></url>\n' for u in urls)+'</urlset>\n',encoding='utf8')
        (DEST/'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: '+base+'sitemap.xml\n',encoding='utf8')
    print(f'Ready: {len(list(DEST.rglob("index.html")))} clean-URL pages; canonical base: {base or "preview only"}')

if __name__ == '__main__':
    main()
