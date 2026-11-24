# Study guide build

- `content/NN-slug.html`: chapter text (HTML fragments, KaTeX math with `\( \)` and `$$ $$`).
  Shortcodes: `{{fig:name|caption}}` inserts a diagram from `figures.py`; `{{flow:transmission}}` inserts the monetary-transmission flow chart.
- `figures.py`: every diagram, computed from the same equations as the worked examples.
- `style.css`: copied to `src/assets/style.css` at build time.
- `index_intro.html`: the "How to use" section on the home page and in the PDF.

Rebuild the website (`src/`) and the PDF (needs Microsoft Edge or Chrome and an internet connection for KaTeX and fonts):

```
python tools/build.py           # site + PDF
python tools/build.py --no-pdf  # site only
```

Preview locally: `python -m http.server 8765 --directory src`, then open http://localhost:8765.
