#!/usr/bin/env python3
"""Prepare the public, static GitHub Pages artifact from the editable site folder."""
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from io import BytesIO
from time import sleep
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

# An earlier successful release already hosts the approved source images.
# Prefer those stable copies to avoid depending on temporary outages at
# the university, research foundation, or portrait hosts during deployment.
PUBLISHED_ASSET_BASE = 'https://majdialomari.com/assets/'


PRIMARY_DOMAIN = 'majdialomari.com'
SOCIAL_FILENAME = 'majdi-social-preview-v2.jpg'
SOCIAL_SIZE = (1200, 630)
SOCIAL_LIMIT = 590_000


def build_social_image(original, output):
    """Generate a sharp, landscape social card from the unchanged source photo."""
    from io import BytesIO
    from PIL import Image, ImageDraw, ImageFont, ImageOps

    with Image.open(original) as raw:
        photo = ImageOps.exif_transpose(raw).convert('RGB')

    # This is only a *display derivative* for social links. The webpage photo
    # remains the exact source JPEG, byte-for-byte, without recompression.
    card = Image.new('RGB', SOCIAL_SIZE, (248, 247, 244))
    portrait_width = 640
    target_h = SOCIAL_SIZE[1]
    factor = max(portrait_width / photo.width, target_h / photo.height)
    resized = photo.resize((round(photo.width * factor), round(photo.height * factor)), Image.Resampling.LANCZOS)
    left = (resized.width - portrait_width) // 2
    top = max(0, min(resized.height - target_h, round((resized.height - target_h) * 0.12)))
    card.paste(resized.crop((left, top, left + portrait_width, top + target_h)), (0, 0))

    draw = ImageDraw.Draw(card)
    forest = (33, 59, 48)
    muted = (88, 110, 97)
    accent = (177, 138, 101)
    x = 681
    draw.line(((x, 150), (x, 208)), fill=accent, width=3)

    def font(size, serif=False):
        families = ([
            '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf',
            '/usr/share/fonts/truetype/liberation2/LiberationSerif-Regular.ttf',
        ] if serif else [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf',
        ])
        for path in families:
            if Path(path).exists():
                return ImageFont.truetype(path, size)
        return ImageFont.load_default()

    title_lines = ['Dr. Majdi M.', 'Alomari']
    title_size = 58
    while title_size > 32 and any(draw.textbbox((0, 0), line, font=font(title_size, True))[2] > 480 for line in title_lines):
        title_size -= 2
    title_font = font(title_size, True)
    draw.text((x, 237), title_lines[0], font=title_font, fill=forest)
    draw.text((x, 312), title_lines[1], font=title_font, fill=forest)
    draw.text((x, 439), 'Associate Professor', font=font(26), fill=muted)
    draw.text((x, 477), 'of Electrical Engineering', font=font(23), fill=muted)
    draw.text((x, 570), 'AUSTRALIAN UNIVERSITY · KUWAIT', font=font(17), fill=forest)

    for quality in (96, 93, 90, 87, 84, 80, 76):
        data = BytesIO()
        card.save(data, 'JPEG', quality=quality, subsampling=0, optimize=True)
        if data.tell() <= SOCIAL_LIMIT:
            output.write_bytes(data.getvalue())
            break
    else:
        raise SystemExit('The share image could not be kept under the WhatsApp-friendly size limit.')
    print(f'Original portrait: {photo.width}x{photo.height}; unchanged on the site. '
          f'Social preview: {SOCIAL_SIZE[0]}x{SOCIAL_SIZE[1]}, {output.stat().st_size // 1024} KB.')


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


def image_is_valid(data, magic):
    """Reject HTML error pages, empty responses, or corrupt image downloads."""
    if len(data) < 1000 or not data.startswith(magic):
        return False
    try:
        from PIL import Image
        with Image.open(BytesIO(data)) as candidate:
            candidate.verify()
        return True
    except Exception:
        return False


def obtain(source, dest, magic, strict):
    """Use approved, unmodified images; survive temporary source-server errors."""
    if dest.is_file() and image_is_valid(dest.read_bytes(), magic):
        return
    if dest.exists():
        dest.unlink()

    # The existing live site's file is the exact approved asset published by
    # a prior successful build. Never replace it with an unrelated logo.
    candidates = (PUBLISHED_ASSET_BASE + dest.name, source)
    failures = []
    for url in candidates:
        for attempt in range(2):
            try:
                req = Request(url, headers={
                    'User-Agent': 'Mozilla/5.0 (compatible; MajdiAlomariSiteBuilder/1.0)',
                    'Accept': 'image/avif,image/webp,image/png,image/jpeg,image/*;q=0.8',
                    'Cache-Control': 'no-cache',
                })
                with urlopen(req, timeout=22) as response:
                    data = response.read(14_000_001)
                if not image_is_valid(data, magic):
                    raise ValueError('the response was not a valid original image')
                dest.write_bytes(data)
                print(f'Approved asset ready: {dest.name} (source: {url})')
                return
            except Exception as error:
                failures.append(f'{url}: {error}')
                if attempt == 0:
                    sleep(1.0)
    if strict:
        raise SystemExit(
            f'Unable to obtain the approved image {dest.name}. '
            f'For a permanent fix, save the authentic file to '
            f'site/assets/{dest.name} and commit it. '
            f'Attempted the published-site copy and the original source. '
            f'Details: {"; ".join(failures)}'
        )
    print(f'Asset not locally available for preview: {dest.name}')


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
    if base:
        build_social_image(DEST / 'assets' / ORIGINALS['portrait'][1], DEST / 'assets' / SOCIAL_FILENAME)
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
            photo_url = base + 'assets/' + SOCIAL_FILENAME
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
                      '\n    <meta property="og:image:width" content="1200"/>'
                      '\n    <meta property="og:image:height" content="630"/>'
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
