# Dr. Majdi M. Alomari — academic website

A static, GitHub Pages-compatible academic site. The public files are in `site/`; the deployment workflow publishes only the generated `dist/` folder, never the repository scripts or documentation.

## Pages and URLs

The homepage is `/`, with `/research/`, `/publications/`, `/profile/` and individual publications at `/papers/<paper-slug>/`. The browser does not display `.html` filenames. Each page has a real `index.html` file inside its directory, so direct links work without a JavaScript router.

## Publish on GitHub Pages

1. Put these files into the root of a GitHub repository. Keep `.github/` and `scripts/`.
2. Under **Settings → Pages**, select **GitHub Actions**.
3. Push to `main`. The workflow vendors the original photo and institutional logos into the published site, checks links/SEO and deploys.
4. If any original image host rejects automatic download, obtain the **approved original** yourself and place it in `site/assets/` using the filenames below. Do not substitute an unrelated photograph or logo.
5. Optional custom domain: add `site/CNAME` containing only the hostname, then configure the same domain in GitHub's Pages settings and update DNS.
6. Once deployed, submit `https://YOUR-DOMAIN/sitemap.xml` to Google Search Console.

Images used by the build: `site/assets/majdi-portrait-original.jpg`, `au-official-logo.webp`, `kfas-official-logo.png`. The build fails instead of silently using a different image when originals cannot be fetched. No file with an academic CV, home address, personal phone number, references, or private details is included in the published site.

## Editing

To change public content edit `site/index.html`, `site/research/index.html`, `site/publications/index.html`, `site/profile/index.html` or one of `site/papers/<slug>/index.html`.

Shared styles: `site/assets/site.css`. Shared interactions: `site/assets/site.js`. Publication data: `site/assets/publications.json`.

For a local, dependency-free preview build:

```sh
python3 scripts/release.py --preview
```

Then serve `dist/` using a static HTTP server. GitHub Actions uses `python3 scripts/release.py` with the real repository name and validates the result using `python3 scripts/verify.py`.


## Opening the site directly on a computer

For a quick offline preview, open **`site/index.html`** (not the repository root). The navigation automatically targets `research/index.html`, `publications/index.html`, `profile/index.html`, and paper `index.html` files when opened using `file://`. CSS, JavaScript and local pages work without starting a server. The approved portrait and institutional logos are downloaded during the GitHub deployment, so the offline source preview may lack those images until you manually supply them.

For the full live-site experience, including fast client-side transitions, use GitHub Pages or a local HTTP server. Browsers restrict some features, including service workers and automatic route fetching, on `file://`.

## Sharing previews

After publishing, sharing a public `https://` link on WhatsApp or social networks uses a live `og:image` URL pointing to Dr. Alomari’s original portrait on **your own GitHub Pages website**. Social preview images don't work from local `file://` links. Platforms cache previews; updates may take time to propagate. If photo downloading fails, the GitHub build intentionally fails rather than publishing a broken share image.

## Notes

The CV supplied by Dr. Alomari (February 2026) is the source of the academic title and credentials; it is not published in the repository. A site can be optimized for discovery, but search ranking is decided by search engines and cannot be guaranteed.

## Profile motion

Profile section headings, education, professional credentials and appointments have a restrained, single-entry reveal. It starts before the item enters the visible area, with no stagger or hidden content. Scrolling back up does not replay animations; this prevents the page from feeling like it is chasing the reader. Visitors requesting reduced motion receive no reveal animations. The layout, content and routing are otherwise unchanged.
