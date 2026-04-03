#!/usr/bin/env python3

from __future__ import annotations

import json
import random
import re
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path("/root/src/chrome-gpt-backend/big_websites_massive/website/sites/ai-tools-gallery")
OUTPUT = ROOT / "data" / "tools.json"
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


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    tools = materialize_tools()
    payload = {
        "meta": {
            "title": "AI Tools Gallery",
            "count": len(tools),
            "source": "Local TAAFT scrape dataset",
        },
        "tools": tools,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {len(tools)} tools to {OUTPUT}")


if __name__ == "__main__":
    main()
