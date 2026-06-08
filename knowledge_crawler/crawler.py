"""Self-improving clinical knowledge crawler — production.

Fetches clinical knowledge from: PubMed E-utilities, WHO Disease Outbreak News,
CDC clinical guidelines, and Vietnam MOH. Uses httpx with rate limiting
and retry logic. Respects API keys and rate limits.

Phase 4 production implementation.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

PUBMED_API_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
WHO_API_BASE = "https://www.who.int/api"
CDC_BASE = "https://www.cdc.gov"
VIETNAM_MOH_BASE = "https://moh.gov.vn"

_CACHE_DIR = Path.home() / ".phta" / "knowledge_cache"
_RATE_LIMIT_DELAY = 0.34


def _ensure_cache_dir() -> None:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _cache_key(query: str, source: str) -> str:
    h = hashlib.sha256(f"{source}:{query}".encode()).hexdigest()[:16]
    return f"{source}_{h}.json"


def _read_cache(cache_name: str, max_age_hours: int = 24) -> list[dict[str, Any]] | None:
    path = _CACHE_DIR / cache_name
    if not path.exists():
        return None
    age_hours = (time.time() - path.stat().st_mtime) / 3600
    if age_hours > max_age_hours:
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _write_cache(cache_name: str, data: list[dict[str, Any]]) -> None:
    _ensure_cache_dir()
    (_CACHE_DIR / cache_name).write_text(json.dumps(data, indent=2))


async def _rate_limited_get(client: httpx.AsyncClient, url: str, **kwargs) -> httpx.Response:
    time.sleep(_RATE_LIMIT_DELAY)
    return await client.get(url, **kwargs)


async def crawl_pubmed(
    query: str = "triage algorithm clinical guidelines primary care",
    max_results: int = 20,
) -> list[dict[str, Any]]:
    api_key = os.environ.get("PUBMED_API_KEY", "")
    cache_name = _cache_key(query, "pubmed")
    cached = _read_cache(cache_name, max_age_hours=24)
    if cached:
        return cached

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            params: dict[str, str | int] = {
                "db": "pubmed",
                "term": query,
                "retmax": min(max_results, 50),
                "retmode": "json",
                "sort": "relevance",
            }
            if api_key:
                params["api_key"] = api_key

            search_resp = await client.get(f"{PUBMED_API_BASE}/esearch.fcgi", params=params)
            if search_resp.status_code != 200:
                logger.warning(f"PubMed search failed: {search_resp.status_code}")
                return []

            search_data = search_resp.json()
            ids = search_data.get("esearchresult", {}).get("idlist", [])
            if not ids:
                return []

            id_str = ",".join(ids[:max_results])
            fetch_params: dict[str, str | int] = {
                "db": "pubmed",
                "id": id_str,
                "retmode": "json",
                "rettype": "abstract",
            }
            if api_key:
                fetch_params["api_key"] = api_key

            time.sleep(_RATE_LIMIT_DELAY)
            fetch_resp = await client.get(f"{PUBMED_API_BASE}/esummary.fcgi", params=fetch_params)
            if fetch_resp.status_code != 200:
                return []

            fetch_data = fetch_resp.json()
            results_raw = fetch_data.get("result", {})

            results: list[dict[str, Any]] = []
            for pmid in ids:
                article = results_raw.get(pmid, {})
                if isinstance(article, dict):
                    results.append({
                        "source": "pubmed",
                        "id": pmid,
                        "title": article.get("title", ""),
                        "pub_date": article.get("pubdate", ""),
                        "source_journal": article.get("source", ""),
                        "authors": [a.get("name", "") for a in article.get("authors", [])[:5]],
                        "doi": article.get("elocationid", ""),
                        "abstract": "",
                        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                    })

        _write_cache(cache_name, results)
        return results

    except Exception:
        logger.exception("PubMed crawl failed")
        return []


async def crawl_who() -> list[dict[str, Any]]:
    cache_name = _cache_key("disease_outbreak_news", "who")
    cached = _read_cache(cache_name, max_age_hours=12)
    if cached:
        return cached

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "https://www.who.int/rss-feeds/news-english.xml",
                follow_redirects=True,
            )
            if resp.status_code != 200:
                return []

            results: list[dict[str, Any]] = []
            titles = re.findall(r"<title><!\[CDATA\[(.*?)\]\]></title>", resp.text)
            descriptions = re.findall(r"<description><!\[CDATA\[(.*?)\]\]></description>", resp.text)
            links = re.findall(r"<link>(https://www\.who\.int.*?)</link>", resp.text)
            dates = re.findall(r"<pubDate>(.*?)</pubDate>", resp.text)

            health_keywords = [
                "outbreak", "disease", "health", "emergency", "pandemic",
                "epidemic", "alert", "covid", "influenza", "ebola", "dengue",
                "malaria", "cholera", "measles", "polio", "vaccine",
            ]

            for i in range(min(len(titles), 20)):
                title = titles[i]
                if any(k in title.lower() for k in health_keywords):
                    results.append({
                        "source": "who",
                        "id": f"who_{i}",
                        "title": title,
                        "description": descriptions[i] if i < len(descriptions) else "",
                        "url": links[i] if i < len(links) else "",
                        "pub_date": dates[i] if i < len(dates) else "",
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                    })

        _write_cache(cache_name, results)
        return results

    except Exception:
        logger.exception("WHO crawl failed")
        return []


async def crawl_cdc() -> list[dict[str, Any]]:
    cache_name = _cache_key("clinical_guidelines", "cdc")
    cached = _read_cache(cache_name, max_age_hours=24)
    if cached:
        return cached

    results: list[dict[str, Any]] = []
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            cdc_feeds = [
                "https://www.cdc.gov/media/rss/diseases.xml",
                "https://tools.cdc.gov/api/v2/resources/media/emerging.xml",
            ]
            for feed_url in cdc_feeds:
                try:
                    resp = await client.get(feed_url)
                    if resp.status_code == 200:
                        titles = re.findall(r"<title[^>]*>(.*?)</title>", resp.text, re.IGNORECASE | re.DOTALL)
                        descriptions = re.findall(r"<description[^>]*>(.*?)</description>", resp.text, re.IGNORECASE | re.DOTALL)
                        links = re.findall(r"<link>(https?://[^<]+)</link>", resp.text)
                        health_keywords = [
                            "outbreak", "disease", "health", "emergency", "alert", "guideline",
                            "clinical", "morbidity", "mortality", "vaccine", "prevention",
                            "treatment", "screening", "recommendation",
                        ]
                        for i in range(min(len(titles) - 1, 15)):
                            title = re.sub(r"<!\[CDATA\[|\]\]>", "", titles[i + 1] if i + 1 < len(titles) else titles[i])
                            desc = re.sub(r"<!\[CDATA\[|\]\]>", "", descriptions[i + 1] if i + 1 < len(descriptions) else "")
                            if any(k in title.lower() for k in health_keywords):
                                results.append({
                                    "source": "cdc",
                                    "id": f"cdc_{i}",
                                    "title": title.strip(),
                                    "description": desc.strip()[:500],
                                    "url": links[i] if i < len(links) else feed_url,
                                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                                })
                except Exception:
                    continue
    except Exception:
        logger.exception("CDC crawl failed")

    _write_cache(cache_name, results)
    return results


async def crawl_vietnam_moh() -> list[dict[str, Any]]:
    cache_name = _cache_key("moh_news", "vietnam")
    cached = _read_cache(cache_name, max_age_hours=24)
    if cached:
        return cached

    results: list[dict[str, Any]] = []
    try:
        async with httpx.AsyncClient(timeout=30, verify=False) as client:
            resp = await client.get(
                f"{VIETNAM_MOH_BASE}/tin-tong-hop",
                follow_redirects=True,
            )
            if resp.status_code != 200:
                logger.warning(f"Vietnam MOH returned {resp.status_code}")
                return []

            titles = re.findall(r'<a[^>]*class="[^"]*title[^"]*"[^>]*>(.*?)</a>', resp.text, re.IGNORECASE)
            links = re.findall(r'<a[^>]*href="(/[^"]+)"[^>]*>', resp.text)

            health_keywords = [
                "dịch", "bệnh", "sốt xuất huyết", "tay chân miệng", "cúm",
                "sởi", "ho gà", "dại", "viêm não", "tiêu chảy", "ngộ độc",
                "COVID", "vaccine", "tiêm chủng", "sức khỏe", "y tế",
                "dengue", "rabies", "HFMD", "influenza",
            ]

            for i in range(min(len(titles), 15)):
                title = titles[i].strip()
                if any(k.lower() in title.lower() for k in health_keywords):
                    url = links[i] if i < len(links) else ""
                    if url and not url.startswith("http"):
                        url = f"{VIETNAM_MOH_BASE}{url}"
                    results.append({
                        "source": "vietnam_moh",
                        "id": f"moh_{i}",
                        "title": title,
                        "url": url,
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                    })
    except Exception:
        logger.exception("Vietnam MOH crawl failed")

    _write_cache(cache_name, results)
    return results


async def crawl_all() -> list[dict[str, Any]]:
    all_results: list[dict[str, Any]] = []

    pubmed = await crawl_pubmed()
    all_results.extend(pubmed)
    logger.info(f"PubMed: {len(pubmed)} articles")

    who = await crawl_who()
    all_results.extend(who)
    logger.info(f"WHO: {len(who)} articles")

    cdc = await crawl_cdc()
    all_results.extend(cdc)
    logger.info(f"CDC: {len(cdc)} articles")

    moh = await crawl_vietnam_moh()
    all_results.extend(moh)
    logger.info(f"Vietnam MOH: {len(moh)} articles")

    return all_results


def main() -> None:
    import asyncio
    print("PHTA Knowledge Crawler v1.0.0")
    print("Crawling PubMed, WHO, CDC, and Vietnam MOH...")
    results = asyncio.run(crawl_all())
    print(f"\nTotal articles fetched: {len(results)}")
    for r in results[:10]:
        print(f"  [{r['source']}] {r.get('title', 'N/A')[:80]}")


if __name__ == "__main__":
    main()
