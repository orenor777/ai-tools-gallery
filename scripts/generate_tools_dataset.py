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
CATEGORIES_DIR = ROOT / "categories"
TOOLS_DIR = ROOT / "tools"
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


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "item"


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


def clean_image_src(value: str | None) -> str:
    image = normalize_text(value)
    if image.startswith("//"):
        return f"https:{image}"
    return image


def make_tool_slug(name: str, index: int) -> str:
    return f"{slugify(name)}-{index}"


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
                "image_src": clean_image_src(row.get("image_src")),
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
            if not item.get("image_src"):
                item["image_src"] = clean_image_src(row.get("image_src"))
            if isinstance(stats, dict):
                conversations = stats.get("conversations")
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
        category_slug = slugify(category)
        pricing = normalize_text(item.get("pricing")) or random.choice(["Free", "Freemium", "Paid", "Contact for pricing"])
        description = normalize_text(item.get("description")) or f"{item['name']} is an AI tool in the {category} category."
        tagline = description[:140].rstrip(" .,;:")
        url = item["external_url"]
        domain = external_domain(url)
        tool_slug = make_tool_slug(item["name"], index)
        tools.append(
            {
                "id": index,
                "slug": tool_slug,
                "name": item["name"],
                "tagline": tagline,
                "description": description,
                "category": category,
                "category_slug": category_slug,
                "pricing": pricing,
                "url": url,
                "domain": domain,
                "source_page": item.get("source_page") or "",
                "image_src": item.get("image_src") or "",
                "conversations": int(item.get("conversations") or 0),
                "featured": index <= 12,
            }
        )
    return tools


def page_frame(*, title: str, description: str, stylesheet_href: str, app_href: str | None, body: str) -> str:
    script_tag = f'\n    <script src="{app_href}" type="module"></script>' if app_href else ""
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{esc(title)}</title>
    <meta name="description" content="{esc(description)}" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Inter:wght@400;500;600;700&display=swap"
      rel="stylesheet"
    />
    <link rel="stylesheet" href="{stylesheet_href}" />
  </head>
  <body>
{body}{script_tag}
  </body>
</html>
"""


def render_header(home_href: str, browse_href: str) -> str:
    return f"""
      <header class="site-header">
        <a class="brand-lockup brand-link" href="{home_href}">
          <div class="brand-mark">A</div>
          <div>
            <div class="brand-name">AI Tools Gallery</div>
            <div class="brand-subtitle">Static directory seeded from the local TAAFT scrape</div>
          </div>
        </a>
        <a class="header-link" href="{browse_href}">Browse directory</a>
      </header>""".strip()


def render_card(tool: dict, *, detail_prefix: str = ".", category_prefix: str = ".", compact: bool = False) -> str:
    detail_href = f"{detail_prefix}/tools/{tool['slug']}.html" if detail_prefix else f"tools/{tool['slug']}.html"
    category_href = (
        f"{category_prefix}/categories/{tool['category_slug']}.html"
        if category_prefix
        else f"categories/{tool['category_slug']}.html"
    )
    search_blob = " ".join(
        [
            tool["name"],
            tool["category"],
            tool["pricing"],
            tool["domain"],
            tool["description"],
        ]
    ).lower()
    summary = tool["tagline"] or tool["description"]
    return f"""
          <article class="tool-card" data-category="{esc(tool['category'])}" data-search="{esc(search_blob)}">
            <div class="tool-card-top">
              <div>
                <a class="tool-category category-link" href="{category_href}">{esc(tool['category'])}</a>
                <h3 class="tool-name"><a class="tool-name-link" href="{detail_href}">{esc(tool['name'])}</a></h3>
              </div>
              <div class="tool-pricing">{esc(tool['pricing'])}</div>
            </div>
            <p class="tool-description">{esc(summary)}</p>
            <div class="tool-metrics">
              <span class="metric domain">{esc(tool['domain'] or 'Unknown domain')}</span>
            </div>
            <div class="tool-actions">
              <a class="tool-link tool-link-secondary" href="{detail_href}">View details</a>
              <a class="tool-link" href="{esc(tool['url'])}" target="_blank" rel="noreferrer">Visit tool</a>
            </div>
          </article>""".strip()


def render_category_pills(categories: list[str], *, current: str | None, prefix: str) -> str:
    pills = []
    for category in categories:
        slug = slugify(category)
        href = f"{prefix}/categories/{slug}.html" if prefix else f"categories/{slug}.html"
        active = " category-pill-active" if current == category else ""
        pills.append(f'<a class="category-pill{active}" href="{href}">{esc(category)}</a>')
    return "\n".join(pills)


def render_index_page(tools: list[dict]) -> str:
    categories = sorted({tool["category"] for tool in tools if tool["category"]})
    featured = "\n".join(render_card(tool) for tool in tools[:6])
    cards = "\n".join(render_card(tool) for tool in tools)
    options = "\n".join(f'                <option value="{esc(category)}">{esc(category)}</option>' for category in categories)
    category_pills = render_category_pills(categories, current=None, prefix=".")
    body = f"""
    <div class="page-shell">
      {render_header("./index.html", "#directory")}
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
              This demo turns the existing TAAFT parsing pipeline into a static website with dedicated pages for tools
              and categories while keeping the whole experience static and crawler-friendly.
            </p>
            <div class="hero-actions">
              <a class="button button-primary" href="#directory">Explore tools</a>
              <a class="button button-secondary" href="#categories">Browse categories</a>
            </div>
          </div>
          <div class="hero-panel" id="stats">
            <div class="stat-card">
              <div class="stat-label">Seed size</div>
              <div class="stat-value">{len(tools)}</div>
              <div class="stat-footnote">Generated from local JSONL sources</div>
            </div>
            <div class="stat-card">
              <div class="stat-label">Categories</div>
              <div class="stat-value">{len(categories)}</div>
              <div class="stat-footnote">Writing, coding, image, automation, and more</div>
            </div>
            <div class="stat-card stat-card-accent">
              <div class="stat-label">Deployment target</div>
              <div class="stat-value">Render</div>
              <div class="stat-footnote">Static site only, no domain attached yet</div>
            </div>
          </div>
        </section>

        <section class="controls" id="categories">
          <div class="controls-top">
            <div>
              <h2>Categories</h2>
              <p>Open a dedicated landing page for any category, or keep browsing all 500 tools below.</p>
            </div>
          </div>
          <div class="category-pills">
{category_pills}
          </div>
        </section>

        <section class="controls" id="directory">
          <div class="controls-top">
            <div>
              <h2>Tool directory</h2>
              <p>Search by name, filter by category, and open dedicated tool pages.</p>
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
          <div class="featured-grid">
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
    </div>"""
    return page_frame(
        title="AI Tools Gallery",
        description="Browse 500 AI utilities from the local TAAFT dataset across writing, coding, research, image, automation, and more.",
        stylesheet_href="./styles.css",
        app_href="./app.js",
        body=body,
    )


def render_category_page(category: str, tools: list[dict], categories: list[str]) -> str:
    cards = "\n".join(render_card(tool, detail_prefix="..", category_prefix="..") for tool in tools)
    category_pills = render_category_pills(categories, current=category, prefix="..")
    body = f"""
    <div class="page-shell">
      {render_header("../index.html", "../index.html#directory")}
      <main>
        <section class="hero hero-simple">
          <div class="hero-copy">
            <div class="hero-badge">Category page</div>
            <h1>{esc(category)} <span>AI tools</span></h1>
            <p>
              Browse {len(tools)} tools in the {esc(category)} category from the local TAAFT-derived dataset.
            </p>
            <div class="hero-actions">
              <a class="button button-primary" href="../index.html#directory">Back to all tools</a>
            </div>
          </div>
        </section>

        <section class="controls">
          <div class="controls-top">
            <div>
              <h2>All categories</h2>
              <p>Move laterally across the directory through dedicated static category pages.</p>
            </div>
            <div class="results-count">{len(tools)} tools in {esc(category)}</div>
          </div>
          <div class="category-pills">
{category_pills}
          </div>
        </section>

        <section class="directory-section">
          <div class="section-heading">
            <h2>{esc(category)} directory</h2>
            <p>Each tool has its own static detail page and external link.</p>
          </div>
          <div class="tool-grid">
{cards}
          </div>
        </section>
      </main>
    </div>"""
    return page_frame(
        title=f"{category} AI Tools",
        description=f"Browse {len(tools)} {category.lower()} AI tools from the local TAAFT dataset.",
        stylesheet_href="../styles.css",
        app_href=None,
        body=body,
    )


def render_tool_page(tool: dict) -> str:
    image_markup = ""
    if tool["image_src"]:
        image_markup = f"""
            <div class="tool-media-card">
              <img class="tool-media-image" src="{esc(tool['image_src'])}" alt="{esc(tool['name'])} preview" loading="lazy" />
            </div>""".rstrip()
    else:
        image_markup = f"""
            <div class="tool-media-card tool-media-fallback">
              <div class="tool-media-placeholder">{esc(tool['name'][:1])}</div>
              <p>No preview image was present in the local dataset for this tool.</p>
            </div>""".rstrip()

    source_row = ""
    if tool["source_page"]:
        source_row = f"""
            <div class="detail-meta-row">
              <span class="detail-meta-label">Source page</span>
              <a class="detail-inline-link" href="{esc(tool['source_page'])}" target="_blank" rel="noreferrer">View original record</a>
            </div>""".rstrip()

    body = f"""
    <div class="page-shell">
      {render_header("../index.html", "../index.html#directory")}
      <main>
        <section class="tool-detail-hero">
          <div class="tool-detail-copy">
            <div class="detail-breadcrumbs">
              <a href="../index.html">Home</a>
              <span>/</span>
              <a href="../categories/{tool['category_slug']}.html">{esc(tool['category'])}</a>
              <span>/</span>
              <span>{esc(tool['name'])}</span>
            </div>
            <div class="hero-badge">Tool page</div>
            <h1>{esc(tool['name'])}</h1>
            <p class="tool-detail-tagline">{esc(tool['tagline'] or tool['description'])}</p>
            <div class="tool-detail-meta">
              <div class="detail-meta-row">
                <span class="detail-meta-label">Category</span>
                <a class="detail-inline-link" href="../categories/{tool['category_slug']}.html">{esc(tool['category'])}</a>
              </div>
              <div class="detail-meta-row">
                <span class="detail-meta-label">Pricing</span>
                <span>{esc(tool['pricing'])}</span>
              </div>
              <div class="detail-meta-row">
                <span class="detail-meta-label">Domain</span>
                <span>{esc(tool['domain'] or 'Unknown domain')}</span>
              </div>
{source_row}
            </div>
            <div class="hero-actions">
              <a class="button button-primary" href="{esc(tool['url'])}" target="_blank" rel="noreferrer">Visit tool</a>
              <a class="button button-secondary" href="../categories/{tool['category_slug']}.html">More {esc(tool['category'])} tools</a>
            </div>
          </div>
          <div class="tool-detail-media">
{image_markup}
          </div>
        </section>

        <section class="directory-section">
          <div class="section-heading">
            <h2>About this tool</h2>
            <p>Generated as a dedicated static detail page from the local TAAFT-derived dataset.</p>
          </div>
          <div class="tool-detail-body">
            <p>{esc(tool['description'])}</p>
          </div>
        </section>
      </main>
    </div>"""
    return page_frame(
        title=f"{tool['name']} • AI Tools Gallery",
        description=tool["description"],
        stylesheet_href="../styles.css",
        app_href=None,
        body=body,
    )


def write_pages(tools: list[dict]) -> None:
    CATEGORIES_DIR.mkdir(parents=True, exist_ok=True)
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)

    OUTPUT_HTML.write_text(render_index_page(tools))

    categories = sorted({tool["category"] for tool in tools if tool["category"]})
    for category in categories:
        category_tools = [tool for tool in tools if tool["category"] == category]
        (CATEGORIES_DIR / f"{slugify(category)}.html").write_text(render_category_page(category, category_tools, categories))

    for tool in tools:
        (TOOLS_DIR / f"{tool['slug']}.html").write_text(render_tool_page(tool))


def main() -> None:
    tools = materialize_tools()
    write_pages(tools)
    print(
        f"Wrote {len(tools)} tools to {OUTPUT_HTML}, "
        f"{len(list(CATEGORIES_DIR.glob('*.html')))} category pages, "
        f"and {len(list(TOOLS_DIR.glob('*.html')))} tool pages"
    )


if __name__ == "__main__":
    main()
