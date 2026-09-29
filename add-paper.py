#!/usr/bin/env python3
"""Add a paper card to index.html.

Does the mechanical parts: pulls the figure out of the PDF, trims it, converts
it to WebP (plus the 800px copy the card shows), measures the aspect ratio,
picks the next accent colour, and splices the card into the papers grid. It
does not push -- look at the page first.

    ./add-paper.py --pdf ~/Downloads/new.pdf --fig-page 3 \
        --venue "NeurIPS 2026" \
        --title "Some Title" \
        --authors "Jieyuan Pei, A N Other" \
        --paper https://openreview.net/forum?id=XXXX \
        --code  https://github.com/GuobaPei/repo \
        --note  "3.2 dB better at half the compute."

Every flag except --venue and --title is optional. With no --pdf the card is
created without a figure. Run with --list-figures to see what is on a page
before committing to one.
"""
import argparse, os, re, shutil, subprocess, sys, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(HERE, 'index.html')
FIGS = os.path.join(HERE, 'figs')
# same order the existing cards use, so a new one keeps the rotation going
# no yellow: as link text on the cream panel it is 1.4:1, unreadable
COLOURS = ['purple', 'red', 'blue', 'orange', 'green', 'teal', 'pink']


def die(msg):
    sys.exit('error: ' + msg)


def slug(title):
    s = unicodedata.normalize('NFKD', title).encode('ascii', 'ignore').decode()
    s = re.sub(r'[^a-zA-Z0-9]+', '-', s).strip('-').lower()
    return (s[:28] or 'paper').rstrip('-')


def load_fitz():
    try:
        import fitz
        return fitz
    except ImportError:
        die('pymupdf is needed for --pdf.  pip install pymupdf')


def figure_blocks(page):
    """Candidate figure rects on a page: unions of drawings and images, big
    enough to be a figure rather than a rule or a logo."""
    rects = [d['rect'] for d in page.get_drawings()]
    for img in page.get_images(full=True):
        # An image can be listed in the xref without being placed on the page.
        # get_image_rects returns [] for those; get_image_bbox would raise and
        # make pymupdf dump a traceback to stderr even when it is caught.
        placed = page.get_image_rects(img)
        if placed:
            rects.append(placed[0])
    if not rects:
        return []
    # cluster rects that overlap vertically into single figures
    rects.sort(key=lambda r: r.y0)
    groups, cur = [], [rects[0]]
    for r in rects[1:]:
        if r.y0 <= max(x.y1 for x in cur) + 12:
            cur.append(r)
        else:
            groups.append(cur); cur = [r]
    groups.append(cur)
    out = []
    for g in groups:
        x0 = min(r.x0 for r in g); x1 = max(r.x1 for r in g)
        y0 = min(r.y0 for r in g); y1 = max(r.y1 for r in g)
        w, h = x1 - x0, y1 - y0
        if w > page.rect.width * 0.35 and h > 55:      # skip rules and logos
            out.append((x0, y0, x1, y1, w * h))
    out.sort(key=lambda t: -t[4])
    return out


def extract(pdf, page_no, out_png, index=0):
    fitz = load_fitz()
    doc = fitz.open(pdf)
    if not 1 <= page_no <= doc.page_count:
        die(f'--fig-page {page_no} is outside the {doc.page_count}-page pdf')
    page = doc[page_no - 1]
    blocks = figure_blocks(page)
    if not blocks:
        die(f'found no figure-sized block on page {page_no}; try another page '
            f'or --list-figures')
    if index >= len(blocks):
        die(f'page {page_no} has {len(blocks)} candidate figure(s), asked for #{index+1}')
    x0, y0, x1, y1, _ = blocks[index]
    clip = fitz.Rect(x0 - 2, y0 - 2, x1 + 2, y1 + 2)
    page.get_pixmap(matrix=fitz.Matrix(4, 4), clip=clip).save(out_png)
    return out_png


def trim_and_webp(src_png, dest_webp, width=1200):
    from PIL import Image, ImageChops
    im = Image.open(src_png).convert('RGB')
    # trim the white margin the clip leaves behind
    bg = Image.new('RGB', im.size, (255, 255, 255))
    box = ImageChops.difference(im, bg).convert('L').point(lambda p: 255 if p > 12 else 0).getbbox()
    if box:
        im = im.crop((max(0, box[0] - 8), max(0, box[1] - 8),
                      min(im.width, box[2] + 8), min(im.height, box[3] + 8)))
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    # same rule the existing figures were built with: lossless unless lossy is
    # a lot smaller, so diagram text never gets chewed up
    a, b = dest_webp + '.ll', dest_webp + '.q'
    im.save(a, 'WEBP', lossless=True, method=6)
    im.save(b, 'WEBP', quality=90, method=6)
    keep = a if os.path.getsize(a) <= os.path.getsize(b) * 1.35 else b
    os.replace(keep, dest_webp)
    for t in (a, b):
        if os.path.exists(t):
            os.remove(t)
    return im.width, im.height


CARD_W = 800


def card_copy(fig):
    """figs/x.webp -> figs/x-card.webp, the file the card itself loads. Cards show
    figures 300-460 CSS px wide, so the full 1200px file is only fetched when the
    lightbox opens -- about half the bytes on a slow link."""
    from PIL import Image
    im = Image.open(os.path.join(FIGS, fig))
    im = im.convert('RGBA' if 'A' in im.getbands() else 'RGB')
    if im.width > CARD_W:
        im = im.resize((CARD_W, round(im.height * CARD_W / im.width)), Image.LANCZOS)
    name = fig[:-len('.webp')] + '-card.webp'
    im.save(os.path.join(FIGS, name), 'WEBP', quality=82, method=6)
    return name


def next_colour(html):
    used = re.findall(r'<article class="pcard" style="--c:var\(--(\w+)\)', html)
    return COLOURS[len(used) % len(COLOURS)]


def bold_me(authors):
    return re.sub(r'\b(Jieyuan Pei)\b', r'<u>\1</u>', authors)


def build_card(a, colour, fig, dims, thumb):
    esc = lambda s: (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))
    title = esc(a.title)
    head = f'<a href="{esc(a.paper)}">{title}</a>' if a.paper else title
    L = [f'      <article class="pcard" style="--c:var(--{colour})">']
    if fig:
        w, h = dims
        L.append(f'        <a class="pfig" href="figs/{fig}" style="aspect-ratio:{w}/{h}">'
                 f'<img loading="lazy" decoding="async" src="figs/{thumb}" '
                 f'alt="{esc(a.alt or a.title)}"></a>')
    L.append('        <div class="pbody">')
    # Venue only. Submission status is deliberately not shown anywhere: an
    # arXiv id states a fact, "under review at X" announces where you submitted.
    L.append(f'          <div class="tags"><span class="tag">{esc(a.venue)}</span></div>')
    L.append(f'          <p class="pt">{head}</p>')
    if a.authors:
        L.append(f'          <p class="pa">{bold_me(esc(a.authors))}</p>')
    if a.note:
        L.append(f'          <p class="pn">{esc(a.note)}</p>')
    links = []
    for label, url in (('Paper', a.paper), ('Project page', a.project), ('Code', a.code)):
        if url:
            links.append(f'<a href="{esc(url)}">{label} &rarr;</a>')
    if links:
        L.append('          <p class="plink">' + '\n          &nbsp;'.join(links) + '</p>')
    L += ['        </div>', '      </article>', '']
    return '\n'.join(L)


def main():
    p = argparse.ArgumentParser(description='Add a paper card to the homepage.')
    p.add_argument('--title', required=True)
    p.add_argument('--venue', required=True, help='e.g. "NeurIPS 2026" or "arXiv:2606.01234"')
    p.add_argument('--authors', default='', help='full list in printed order')
    p.add_argument('--note', default='', help='one-line headline result')
    p.add_argument('--paper', default='')
    p.add_argument('--code', default='')
    p.add_argument('--project', default='')
    p.add_argument('--pdf', default='', help='pdf to lift the figure from')
    p.add_argument('--fig-page', type=int, default=0, help='1-based page holding the figure')
    p.add_argument('--fig-index', type=int, default=1, help='which candidate on that page (default 1, the largest)')
    p.add_argument('--fig', default='', help='use this image file instead of extracting from a pdf')
    p.add_argument('--alt', default='', help='alt text for the figure')
    p.add_argument('--list-figures', action='store_true', help='list figure candidates per page and exit')
    a = p.parse_args()

    if not os.path.exists(HTML):
        die(f'{HTML} not found — run this from inside the homepage repo')

    if a.list_figures:
        if not a.pdf:
            die('--list-figures needs --pdf')
        fitz = load_fitz()
        doc = fitz.open(os.path.expanduser(a.pdf))
        for i in range(doc.page_count):
            for j, (x0, y0, x1, y1, area) in enumerate(figure_blocks(doc[i]), 1):
                print(f'  page {i+1:>2}  #{j}  {x1-x0:.0f} x {y1-y0:.0f} pt'
                      f'   --fig-page {i+1} --fig-index {j}')
        return

    html = open(HTML, encoding='utf-8').read()
    if a.title.lower() in re.sub(r'<[^>]+>', '', html).lower():
        die('a card with that title is already on the page')

    fig_name, dims = None, None
    if a.fig:
        os.makedirs(FIGS, exist_ok=True)
        fig_name = slug(a.title) + '.webp'
        src = os.path.expanduser(a.fig)
        if src.lower().endswith('.webp'):
            shutil.copy(src, os.path.join(FIGS, fig_name))
            from PIL import Image
            dims = Image.open(os.path.join(FIGS, fig_name)).size
        else:
            dims = trim_and_webp(src, os.path.join(FIGS, fig_name))
    elif a.pdf:
        if not a.fig_page:
            die('--pdf also needs --fig-page (use --list-figures to find it)')
        os.makedirs(FIGS, exist_ok=True)
        fig_name = slug(a.title) + '.webp'
        tmp = os.path.join(FIGS, '.tmp-extract.png')
        extract(os.path.expanduser(a.pdf), a.fig_page, tmp, a.fig_index - 1)
        dims = trim_and_webp(tmp, os.path.join(FIGS, fig_name))
        os.remove(tmp)

    colour = next_colour(html)
    thumb = card_copy(fig_name) if fig_name else None
    card = build_card(a, colour, fig_name, dims, thumb)

    # Splice in after the last existing card. Anchoring on whatever markup
    # follows the grid is brittle -- that is exactly how this broke once, when
    # the block after the grid was deleted from the page.
    try:
        grid = html.index('<div class="pgrid">')
        end = html.index('</section>', grid)
        after_last = grid + html[grid:end].rindex('</article>') + len('</article>')
    except ValueError:
        die('could not locate the papers grid (<div class="pgrid"> ... </section>) '
            'in index.html')
    html = html[:after_last] + '\n\n' + card.rstrip('\n') + html[after_last:]

    # keep the footer date honest
    from datetime import date
    html = re.sub(r'(<p class="upd">Last updated )[^<]*(</p>)',
                  lambda m: m.group(1) + date.today().strftime('%B %Y') + m.group(2), html)

    open(HTML, 'w', encoding='utf-8').write(html)

    print(f'added: {a.title}')
    print(f'  venue  {a.venue}')
    print(f'  colour {colour}')
    if fig_name:
        kb = os.path.getsize(os.path.join(FIGS, fig_name)) / 1024
        print(f'  figure figs/{fig_name}  {dims[0]}x{dims[1]}  {kb:.0f}K')
    else:
        print('  figure none')
    for label, url in (('paper', a.paper), ('code', a.code), ('project', a.project)):
        if url:
            print(f'  {label:6} {url}')
    print('\nCheck it, then:')
    print('  open index.html')
    print('  ./publish.sh "add ' + a.title[:40] + '"')


if __name__ == '__main__':
    main()
