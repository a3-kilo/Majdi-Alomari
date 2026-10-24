(() => {
    'use strict';
    const q = (s, c = document) => c.querySelector(s), qa = (s, c = document) => Array.from(c.querySelectorAll(s));
    const prefersReduced = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
    const cache = new Map();
    const siteRoot = new URL('../', document.currentScript?.src || document.baseURI);
    const mainRoutes = ['', 'research/', 'publications/', 'profile/'];
    let routeSerial = 0;
    let persistentPortrait = null;
    let portraitPromise = null;
    const PHOTO_URL = new URL('majdi-portrait-original.jpg', document.currentScript?.src || new URL('assets/site.js', siteRoot)).href;
    function trackPortrait() {
        const el = q('main img[data-photo-primary]');
        if (el && !persistentPortrait)
            persistentPortrait = el;
    }
    function makePortrait() {
        const img = new Image();
        img.className = 'portrait';
        img.alt = 'Dr. Majdi M. Alomari, Australian University, Kuwait';
        img.width = 1000;
        img.height = 888;
        img.loading = 'eager';
        img.decoding = 'sync';
        img.fetchPriority = 'high';
        img.dataset.photoPrimary = PHOTO_URL;
        img.src = PHOTO_URL;
        return img;
    }
    function warmPortrait() {
        if (!persistentPortrait) {
            trackPortrait();
            if (!persistentPortrait)
                persistentPortrait = makePortrait();
        }
        if (!portraitPromise) {
            portraitPromise = typeof persistentPortrait.decode === 'function'
                ? persistentPortrait.decode().then(() => true, () => false)
                : new Promise(resolve => {
                    if (persistentPortrait.complete)
                        return resolve(persistentPortrait.naturalWidth > 0);
                    persistentPortrait.addEventListener('load', () => resolve(true), { once: true });
                    persistentPortrait.addEventListener('error', () => resolve(false), { once: true });
                });
        }
        return portraitPromise;
    }
    function reusePortrait(nextMain) {
        const placeholder = q('img[data-photo-primary]', nextMain);
        if (!placeholder)
            return;
        if (!persistentPortrait)
            persistentPortrait = placeholder;
        if (placeholder !== persistentPortrait)
            placeholder.replaceWith(persistentPortrait);
    }
    function prepareImages(root = document) {
        qa('img[data-brand-logo]', root).forEach(img => {
            const wrap = img.closest('.institution-visual');
            const fallback = () => wrap?.classList.add('load-error');
            img.addEventListener('error', fallback, { once: true });
            if (img.complete && img.naturalWidth === 0)
                fallback();
        });
    }
    function warmImages() { warmPortrait(); }
    function navUnderline() {
        const nav = q('.site-nav');
        if (!nav)
            return;
        let bar = q('.nav-underline', nav);
        if (!bar) {
            bar = document.createElement('span');
            bar.className = 'nav-underline';
            bar.setAttribute('aria-hidden', 'true');
            nav.appendChild(bar);
        }
        const link = q('a[aria-current="page"]', nav) || q('a', nav);
        if (!link)
            return;
        const a = link.getBoundingClientRect(), b = nav.getBoundingClientRect();
        bar.style.left = (a.left - b.left) + 'px';
        bar.style.width = a.width + 'px';
        bar.classList.add('ready');
    }
    function reveal() {
        if (prefersReduced() || !('IntersectionObserver' in window))
            return;
        const targets = qa('.content-section,.research-areas,.project-item,.year-group,.paper-page').filter(e => !e.dataset.inview);
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(ent => {
                if (!ent.isIntersecting)
                    return;
                observer.unobserve(ent.target);
                ent.target.dataset.inview = '1';
                ent.target.animate([
                    { opacity: .80, transform: 'translateY(13px)' }, { opacity: 1, transform: 'translateY(0)' }
                ], { duration: 450, easing: 'cubic-bezier(.19,1,.22,1)' });
            });
        }, { threshold: .10, rootMargin: '0px 0px -20px 0px' });
        targets.forEach(t => observer.observe(t));
    }
    function normalizePublicationText(value) {
        return String(value || '').normalize('NFKD').replace(/[\u0300-\u036f]/g, '')
            .toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
    }
    function publicationSearchIndex(el) {
        const text = [el.dataset.search || '', el.textContent || '',
            ...qa('a[href]', el).map(a => a.getAttribute('href') || '')].join(' ');
        let normal = normalizePublicationText(text);
        if (normal.includes('photovoltaic'))
            normal += ' pv solar';
        if (normal.includes('gas insulated switchgear'))
            normal += ' gis';
        if (normal.includes('subsynchronous resonance'))
            normal += ' ssr';
        if (normal.includes('sf6'))
            normal += ' sulfur hexafluoride';
        return normal;
    }
    function scrollToPublicationResults() {
        const results = q('.publication-results');
        if (!results)
            return;
        const headerHeight = q('.site-header')?.getBoundingClientRect().height || 0;
        const y = Math.max(0, window.scrollY + results.getBoundingClientRect().top - headerHeight - 16);
        requestAnimationFrame(() => window.scrollTo({ top: y, behavior: prefersReduced() ? 'instant' : 'smooth' }));
    }
    // Profile motion is deliberately short and non-blocking. Reveal each item once,
    // slightly before it reaches the viewport, then leave it fully visible.
    function revealMilestones() {
        if (prefersReduced() || !('IntersectionObserver' in window)) return;
        const main = q('main#main');
        if (!main || !q('.profile-layout', main)) return;

        const targets = qa(
            '.profile-block > h2, .profile-block .milestone, ' +
            '.profile-block .standing-list > div, .profile-block .honours > p',
            main
        );
        const observer = new IntersectionObserver(entries => {
            entries.forEach(({ target, isIntersecting }) => {
                if (!isIntersecting) return;
                observer.unobserve(target);
                if (target.dataset.profileRevealed) return;
                target.dataset.profileRevealed = 'true';

                // Small movement and no delay: fast scrolling never hides content.
                target.animate([
                    { opacity: 0.94, transform: 'translateY(5px)' },
                    { opacity: 1, transform: 'translateY(0)' }
                ], {
                    duration: 220,
                    delay: 0,
                    easing: 'cubic-bezier(.16, 1, .3, 1)'
                });
            });
        }, {
            threshold: 0,
            rootMargin: '0px 0px 160px 0px'
        });
        targets.forEach(target => observer.observe(target));
    }
    // Folder routes work on a web server, but a file:// browser doesn't serve
    // a directory's index.html automatically. Rewrite only for offline viewing.
    function enableLocalFileLinks(root = document) {
        if (location.protocol !== 'file:') return;
        qa('a[href]', root).forEach(link => {
            const raw = link.getAttribute('href');
            if (!raw || raw.startsWith('#') || /^(?:mailto:|tel:|https?:|data:|javascript:)/i.test(raw)) return;
            const url = new URL(raw, document.baseURI);
            if (url.protocol === 'file:' && url.pathname.endsWith('/')) {
                link.href = url.href.replace(/(\?|#|$)/, 'index.html$1');
            }
        });
    }
    function bindPageFeatures() {
        const input = q('#publication-search');
        if (input) {
            let type = 'All';
            const items = qa('.publication'), years = qa('.year-group'), count = q('#results-count'), empty = q('#no-results');
            const indexed = items.map(el => ({ el, search: publicationSearchIndex(el) }));
            const filters = qa('[data-type-filter]');
            const update = () => {
                const words = normalizePublicationText(input.value).split(' ').filter(Boolean);
                let found = 0;
                indexed.forEach(({ el, search }) => {
                    const visible = (type === 'All' || el.dataset.kind === type) && words.every(word => search.includes(word));
                    el.hidden = !visible;
                    if (visible)
                        found++;
                });
                years.forEach(y => {
                    const n = qa('.publication:not([hidden])', y).length;
                    y.hidden = n === 0;
                    const label = q('[data-year-count]', y);
                    if (label)
                        label.textContent = `${n} ${n === 1 ? 'work' : 'works'}`;
                });
                if (count)
                    count.textContent = `${found} ${found === 1 ? 'work' : 'works'}`;
                if (empty)
                    empty.hidden = found !== 0;
            };
            input.addEventListener('input', () => { update(); });
            filters.forEach(b => b.addEventListener('click', () => {
                type = b.dataset.typeFilter;
                filters.forEach(x => x.setAttribute('aria-pressed', String(x === b)));
                update();
                scrollToPublicationResults();
            }));
            update();
        }
        qa('[data-expand]').forEach(b => b.addEventListener('click', () => {
            const el = document.getElementById(b.getAttribute('aria-controls'));
            if (!el)
                return;
            const open = b.getAttribute('aria-expanded') !== 'true';
            b.setAttribute('aria-expanded', String(open));
            el.classList.toggle('open', open);
        }));
        qa('[data-copy-citation]').forEach(b => b.addEventListener('click', async () => { try {
            await navigator.clipboard.writeText(b.dataset.copyCitation);
            b.textContent = 'Copied';
            setTimeout(() => b.textContent = 'Copy citation', 1400);
        }
        catch {
            b.textContent = 'Copy unavailable';
        } }));
        reveal();
        revealMilestones();
        prepareImages(q('main#main') || document);
    }
    function urlForLink(el) {
        if (!el || el.hasAttribute('download') || el.target || el.getAttribute('href')?.startsWith('#'))
            return null;
        const url = new URL(el.href, location.href);
        if (url.origin !== location.origin || !url.pathname.startsWith(siteRoot.pathname) || (!url.pathname.endsWith('/') && !url.pathname.endsWith('/index.html')))
            return null;
        return url;
    }
    async function getDocument(url) {
        const key = url.pathname;
        if (cache.has(key))
            return cache.get(key);
        const task = fetch(url.href, { credentials: 'same-origin' }).then(async (r) => { if (!r.ok)
            throw Error('HTTP ' + r.status); const text = await r.text(); const doc = new DOMParser().parseFromString(text, 'text/html'); if (!q('main#main', doc))
            throw Error('No main element'); return doc; }).catch(err => { cache.delete(key); throw err; });
        cache.set(key, task);
        return task;
    }
    function updateHead(doc) {
        document.title = doc.title;
        const description = q('meta[name="description"]', doc)?.content;
        if (description && q('meta[name="description"]'))
            q('meta[name="description"]').content = description;
        qa('meta[name^="citation_"]').forEach(el => el.remove());
        qa('meta[name^="citation_"]', doc).forEach(el => document.head.appendChild(el.cloneNode(true)));
        qa('script[type="application/ld+json"]').forEach(el => el.remove());
        qa('script[type="application/ld+json"]', doc).forEach(el => document.head.appendChild(el.cloneNode(true)));
        // Update social metadata when the visible page changes without reloading.
        ['og:title', 'og:description', 'og:image', 'og:image:alt', 'og:url'].forEach(name => {
            const fresh = q(`meta[property="${name}"]`, doc);
            const old = q(`meta[property="${name}"]`);
            if (fresh && old) old.content = fresh.content;
        });
        const canonical = q('link[rel="canonical"]', doc);
        q('link[rel="canonical"]')?.remove();
        if (canonical)
            document.head.appendChild(canonical.cloneNode(true));
    }
    function markActive(path) { qa('.site-nav a').forEach(a => { if (new URL(a.href).pathname.replace(/index\.html$/, '') === path.replace(/index\.html$/, ''))
        a.setAttribute('aria-current', 'page');
    else
        a.removeAttribute('aria-current'); }); navUnderline(); }
    const http = location.protocol === 'https:' || location.protocol === 'http:';
    async function navigate(url, { restore = false } = {}) {
        const seq = ++routeSerial;
        try {
            const doc = await getDocument(url);
            if (seq !== routeSerial)
                return;
            const incoming = q('main#main', doc), current = q('main#main');
            if (!incoming || !current)
                throw Error('Invalid route');
            if (q('img[data-photo-primary]', incoming))
                await warmPortrait();
            if (seq !== routeSerial)
                return;
            const swap = () => {
                if (seq !== routeSerial)
                    return;
                const mounted = document.importNode(incoming, true);
                reusePortrait(mounted);
                current.replaceWith(mounted);
                updateHead(doc);
                markActive(url.pathname);
                bindPageFeatures();
                if (!restore)
                    history.pushState({ page: url.pathname }, '', url.pathname + url.search + url.hash);
                window.scrollTo({ top: 0, behavior: 'instant' });
            };
            if (!prefersReduced() && document.startViewTransition) {
                await document.startViewTransition(swap).finished;
            }
            else if (!prefersReduced() && current.animate) {
                await current.animate([{ opacity: 1, transform: 'none' }, { opacity: 0, transform: 'none' }], { duration: 170, easing: 'ease-in', fill: 'forwards' }).finished.catch(() => { });
                if (seq !== routeSerial)
                    return;
                swap();
                q('main#main')?.animate([{ opacity: 0, transform: 'none' }, { opacity: 1, transform: 'none' }], { duration: 360, easing: 'cubic-bezier(.2,.8,.2,1)' });
            }
            else
                swap();
        }
        catch (e) {
            location.assign(url.href);
        }
    }
    function attachRouting() {
        if (!http || !history.pushState || !window.fetch)
            return;
        document.addEventListener('click', event => {
            if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey)
                return;
            const link = event.target.closest('a[href]');
            const url = urlForLink(link);
            if (!url)
                return;
            if (url.pathname === location.pathname && !url.hash) {
                event.preventDefault();
                window.scrollTo({ top: 0, behavior: 'smooth' });
                return;
            }
            event.preventDefault();
            navigate(url);
        });
        const prewarm = ev => { const link = ev.target.closest('a[href]'); const url = urlForLink(link); if (url)
            getDocument(url).catch(() => { }); };
        document.addEventListener('pointerover', prewarm);
        document.addEventListener('focusin', prewarm);
        addEventListener('popstate', () => navigate(new URL(location.href), { restore: true }));
        const warm = () => mainRoutes.forEach(f => getDocument(new URL(f, siteRoot)).catch(() => { }));
        if ('requestIdleCallback' in window)
            requestIdleCallback(warm, { timeout: 2000 });
        else
            setTimeout(warm, 900);
        if ('serviceWorker' in navigator)
            addEventListener('load', () => navigator.serviceWorker.register(new URL('sw.js', siteRoot).href, {scope: siteRoot.pathname}).catch(() => { }), { once: true });
    }
    enableLocalFileLinks();
    prepareImages();
    trackPortrait();
    bindPageFeatures();
    navUnderline();
    warmImages();
    attachRouting();
    if (location.protocol === 'https:' || location.protocol === 'http:')
        document.documentElement.classList.add('live-navigation');
    addEventListener('resize', navUnderline, { passive: true });
    addEventListener('pageshow', navUnderline);
})();
