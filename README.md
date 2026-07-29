# guobapei.github.io

Personal academic homepage of Jieyuan Pei (裴杰远) — 浙江工业大学 / Zhejiang University of Technology.

<https://guobapei.github.io/>

Static `index.html`, no build step. Edit, commit, push — Pages redeploys.

## Adding a paper

Find which page holds the figure you want:

```bash
./add-paper.py --title x --venue x --pdf ~/Downloads/new.pdf --list-figures
```

Then add the card. It extracts the figure, trims it, converts to WebP, measures
the aspect ratio, picks the next accent colour, bolds your name in the author
list, and refreshes the "last updated" line:

```bash
./add-paper.py \
  --pdf ~/Downloads/new.pdf --fig-page 3 \
  --venue "NeurIPS 2026" \
  --title "Full Paper Title" \
  --authors "First Author, Jieyuan Pei, Last Author" \
  --note "One-line headline result." \
  --paper https://openreview.net/forum?id=XXXX \
  --code  https://github.com/GuobaPei/repo
```

Look at it, then publish. This refuses to push if `index.html` references an
image that does not exist, and waits until the live page matches local:

```bash
./publish.sh "add NeurIPS paper"
```

Useful extras: `--status "Under review"` for an unpublished entry (do not name
the venue you submitted to), `--project URL`, `--fig-index 2` for the second
figure on a page, `--fig some.png` to supply an image instead of a PDF, and no
`--pdf` at all for a card with no figure.
