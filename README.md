# AI Tools Gallery

Static AI tools directory generated from the local TAAFT scrape dataset.

The generator creates:

- `index.html` with the full 500-tool directory
- `categories/*.html` static category pages
- `tools/*.html` static tool detail pages

## Data source

- `/root/data/scraperli/taaft.results.jsonl`
- `/root/data/scraperli/alphabetical_results.jsonlines`

## Local workflow

```bash
cd /root/src/chrome-gpt-backend/big_websites_massive/website/sites/ai-tools-gallery
python3 scripts/generate_tools_dataset.py
python3 -m http.server 8031
```

Then open `http://127.0.0.1:8031`.

## Render deployment

This is a plain static site:

- Build command: leave empty
- Publish directory: `.`

Or use a simple no-op build command like:

```bash
echo "static site"
```
