#!/usr/bin/env python3

from __future__ import annotations

import html
import json
import random
import re
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path("/root/src/chrome-gpt-backend/big_websites_massive/website/sites/ai-tools-gallery")
OUTPUT_HTML = ROOT / "index.html"
PRIMARY = Path("/root/data/scraperli/taaft.results.jsonl")
SECONDARY = Path("/root/data/scraperli/alphabetical_results.jsonlines")
MAX_TOOLS = 500
RANDOM_SEED = 42

FALLBACK_CATEGORIES = [
    "Writing",
    "Research",
    "Coding",
    "Marketing",
    "Image",
    "Video",
    "Voice",
    "Productivity",
    "Education",
    "Analytics",
    "Automation",
    "Design",
]

CATEGORY_RULES = [
    ("Image", ["image", "photo", "avatar", "visual", "art", "logo", "design", "gif", "animation"]),
    ("Video", ["video", "film", "youtube", "subtitle", "editing"]),
    ("Voice", ["audio", "voice", "speech", "transcription", "podcast", "music"]),
    ("Writing", ["writing", "essay", "copy", "blog", "headline", "email", "caption", "translation", "grammar"]),
    ("Coding", ["coding", "code", "developer", "devops", "programming", "api", "software", "sql"]),
    ("Research", ["research", "analysis", "academic", "papers", "search", "document", "summaries"]),
    ("Marketing", ["marketing", "seo", "ads", "social", "sales", "branding", "reviews"]),
    ("Productivity", ["calendar", "meeting", "assistant", "workflow", "productivity", "scheduling"]),
    ("Automation", ["automation", "agents", "integration", "process", "ops"]),
    ("Business", ["business", "finance", "legal", "contracts", "hr", "consulting", "kpi"]),
    ("Education", ["lesson", "tutor", "learning", "study", "preparation", "coach"]),
    ("Lifestyle", ["health", "fitness", "travel", "food", "career", "fashion", "dating", "wellness"]),
]


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def category_from_task(task: str) -> str:
    task = normalize_text(task)
    if not task:
        return ""
    lowered = task.lower()
    for category, keywords in CATEGORY_RULES:
        if any(keyword in lowered for keyword in keywords):
            return category
    return ""


def external_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


def make_slug(name: str, index: int) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return f"{base or 'tool'}-{index}"


def load_primary_records() -> dict[str, dict]:
    records: dict[str, dict] = {}
    if not PRIMARY.exists():
        return records
    with PRIMARY.open() as handle:
        for line in handle:
            row = json.loads(line)
            name = normalize_text(row.get("data_name"))
            description = normalize_text(row.get("description")) or f"{name} is an AI tool discovered from the local TAAFT scrape."
            external_url = normalize_text(row.get("external_url") or row.get("data_url"))
            if not name or not external_url:
                continue
            key = external_url.lower()
            if key in records:
                continue
            records[key] = {
                "name": name,
                "description": description,
                "external_url": external_url,
                "source_page": normalize_text(row.get("data_url")),
                "image_src": normalize_text(row.get("image_src")),
            }
    return records


def merge_secondary(records: dict[str, dict]) -> None:
    if not SECONDARY.exists():
        return
    with SECONDARY.open() as handle:
        for line in handle:
            row = json.loads(line)
            external_url = normalize_text(row.get("external_url") or row.get("page_url"))
            if not external_url:
                continue
            key = external_url.lower()
            task = category_from_task(row.get("task", ""))
            stats = row.get("stats") or {}
            item = records.get(key)
            if item is None:
                name = normalize_text(row.get("name"))
                if not name:
                    continue
                item = {
                    "name": name,
                    "description": f"{name} is listed in the local TAAFT dataset.",
                    "external_url": external_url,
                    "source_page": normalize_text(row.get("page_url")),
                    "image_src": "",
                }
                records[key] = item
            if task and not item.get("category"):
                item["category"] = task
            if row.get("pricing") and not item.get("pricing"):
                item["pricing"] = normalize_text(row.get("pricing"))
            if isinstance(stats, dict):
                saves = stats.get("saves")
                conversations = stats.get("conversations")
                if saves is not None:
                    item["saves"] = saves
                if conversations is not None:
                    item["conversations"] = conversations


def materialize_tools() -> list[dict]:
    random.seed(RANDOM_SEED)
    records = load_primary_records()
    merge_secondary(records)
    items = list(records.values())
    random.shuffle(items)
    selected = items[:MAX_TOOLS]
    tools: list[dict] = []
    for index, item in enumerate(selected, start=1):
        category = normalize_text(item.get("category")) or random.choice(FALLBACK_CATEGORIES)
        pricing = normalize_text(item.get("pricing")) or random.choice(["Free", "Freemium", "Paid", "Contact for pricing"])
        description = normalize_text(item.get("description")) or f"{item['name']} is an AI tool in the {category} category."
        url = item["external_url"]
        domain = external_domain(url)
        tools.append(
            {
                "id": index,
                "slug": make_slug(item["name"], index),
                "name": item["name"],
                "tagline": description[:140],
                "description": description,
                "category": category,
                "pricing": pricing,
                "url": url,
                "domain": domain,
                "source_page": item.get("source_page") or "",
                "saves": int(item.get("saves") or 0),
                "conversations": int(item.get("conversations") or 0),
                "featured": index <= 12,
            }
        )
    return tools


def format_metric(label: str, value: int) -> str:
    if not value:
        return "Dataset pick"
    return f"{label}: {value:,}"


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def render_card(tool: dict) -> str:
    search_blob = " ".join(
        [
            tool["name"],
            tool["category"],
            tool["pricing"],
            tool["domain"],
            tool["description"],
        ]
    ).lower()
    return f"""
          <article
            class="tool-card"
            data-category="{esc(tool['category'])}"
            data-search="{esc(search_blob)}"
          >
            <div class="tool-card-top">
              <div>
                <div class="tool-category">{esc(tool['category'])}</div>
                <h3 class="tool-name">{esc(tool['name'])}</h3>
              </div>
              <div class="tool-pricing">{esc(tool['pricing'])}</div>
            </div>
            <p class="tool-description">{esc(tool['tagline'] or tool['description'])}</p>
            <div class="tool-metrics">
              <span class="metric saves">{esc(format_metric('Saves', tool['saves']))}</span>
              <span class="metric domain">{esc(tool['domain'] or 'Unknown domain')}</span>
            </div>
            <div class="tool-actions">
              <a class="tool-link" href="{esc(tool['url'])}" target="_blank" rel="noreferrer">Visit tool</a>
            </div>
          </article>""".strip()


def render_page(tools: list[dict]) -> str:
    categories = sorted({tool["category"] for tool in tools if tool["category"]})
    featured = "\n".join(render_card(tool) for tool in tools[:6])
    cards = "\n".join(render_card(tool) for tool in tools)
    options = "\n".join(
        f'                <option value="{esc(category)}">{esc(category)}</option>' for category in categories
    )
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>AI Tools Gallery</title>
    <meta
      name="description"
      content="Browse 500 AI utilities from the local TAAFT dataset across writing, coding, research, image, automation, and more."
    />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Inter:wght@400;500;600;700&display=swap"
      rel="stylesheet"
    />
    <link rel="stylesheet" href="./styles.css" />
  </head>
  <body>
    <div class="page-shell">
      <header class="site-header">
        <div class="brand-lockup">
          <div class="brand-mark">A</div>
          <div>
            <div class="brand-name">AI Tools Gallery</div>
            <div class="brand-subtitle">Static directory seeded from the local TAAFT scrape</div>
          </div>
        </div>
        <a class="header-link" href="#directory">Browse directory</a>
      </header>

      <main>
        <section class="hero">
          <div class="hero-copy">
            <div class="hero-badge">500 tools. Pre-rendered HTML. Ready for Render.</div>
            <h1>
              A static directory for
              <span>AI utilities</span>
              built from local scrape data.
            </h1>
            <p>
              This demo turns the existing TAAFT parsing pipeline into a static website with the tool cards rendered
              directly into the page for search engines and lightweight hosting.
            </p>
            <div class="hero-actions">
              <a class="button button-primary" href="#directory">Explore tools</a>
              <a class="button button-secondary" href="#stats">View stats</a>
            </div>
          </div>
          <div class="hero-panel" id="stats">
            <div class="stat-card">
              <div class="stat-label">Seed size</div>
              <div class="stat-value" id="stat-count">{len(tools)}</div>
              <div class="stat-footnote">Generated from local JSONL sources</div>
            </div>
            <div class="stat-card">
              <div class="stat-label">Categories</div>
              <div class="stat-value" id="stat-categories">{len(categories)}</div>
              <div class="stat-footnote">Writing, coding, image, automation, and more</div>
            </div>
            <div class="stat-card stat-card-accent">
              <div class="stat-label">Deployment target</div>
              <div class="stat-value">Render</div>
              <div class="stat-footnote">Static site only, no domain attached yet</div>
            </div>
          </div>
        </section>

        <section class="controls" id="directory">
          <div class="controls-top">
            <div>
              <h2>Tool directory</h2>
              <p>Search by name, filter by category, and open tools directly.</p>
            </div>
            <div class="results-count" id="results-count">{len(tools)} matching tools</div>
          </div>
          <div class="controls-row">
            <label class="search-field">
              <span>Search</span>
              <input id="search-input" type="search" placeholder="Search tools, categories, or domains" />
            </label>
            <label class="filter-field">
              <span>Category</span>
              <select id="category-select">
                <option value="all">All categories</option>
{options}
              </select>
            </label>
          </div>
        </section>

        <section class="featured-section">
          <div class="section-heading">
            <h2>Featured picks</h2>
            <p>A rotating set from the dataset to make the first screen feel curated.</p>
          </div>
          <div class="featured-grid" id="featured-grid">
{featured}
          </div>
        </section>

        <section class="directory-section">
          <div class="section-heading">
            <h2>All tools</h2>
            <p>Pre-rendered static HTML with lightweight client-side filtering.</p>
          </div>
          <div class="tool-grid" id="tool-grid">
{cards}
          </div>
        </section>
      </main>
    </div>

    <script src="./app.js" type="module"></script>
  </body>
</html>
"""


def main() -> None:
    tools = materialize_tools()
    OUTPUT_HTML.write_text(render_page(tools))
    print(f"Wrote {len(tools)} tools to {OUTPUT_HTML}")


if __name__ == "__main__":
    main()
