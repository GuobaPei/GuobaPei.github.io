# guobapei.github.io

Personal academic homepage of Jieyuan Pei (裴杰远) — 浙江工业大学 / Zhejiang University of Technology.

<https://guobapei.github.io/>

Static `index.html`, no build step. Edit, commit, push — Pages redeploys.

## Adding a paper

Find which page holds the figure you want:

```bash
./add-paper.py --title x --venue x --pdf ~/Downloads/new.pdf --list-figures
```

Then add the card. It extracts the figure, trims it, converts to WebP (plus the
800px copy the card loads; the full size only opens in the lightbox), measures
the aspect ratio, picks the next accent colour, bolds your name in the author
list, turns `Name*` (equal contribution) and `Name†` (corresponding author) into
superscripts, and refreshes the "last updated" line:

```bash
./add-paper.py \
  --pdf ~/Downloads/new.pdf --fig-page 3 \
  --venue "NeurIPS 2026" \
  --title "Full Paper Title" \
  --authors "Jieyuan Pei*, Second Author*, Last Author†" \
  --note "One-line headline result." \
  --paper https://openreview.net/forum?id=XXXX \
  --code  https://github.com/GuobaPei/repo
```

Look at it, then publish. This refuses to push if `index.html` references an
image that does not exist, and waits until the live page matches local:

```bash
./publish.sh "add NeurIPS paper"
```

Useful extras: `--project URL`, `--fig-index 2` for the second figure on a page,
`--fig some.png` to supply an image instead of a PDF, and no `--pdf` at all for
a card with no figure.

For a paper that is not published yet, put the arXiv id in `--venue`
(`--venue "arXiv:2606.01234"`) and stop there. Submission status is never shown:
an arXiv id is a fact, "under review at X" announces where you submitted.
