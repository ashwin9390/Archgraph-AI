"""
ArchGraph AI — Ingestion Component
Async fetcher with requests → Playwright fallback, robots.txt compliance,
streak-based alerting, and clean Markdown output.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import aiohttp
from bs4 import BeautifulSoup

try:
    from markdownify import markdownify as md
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "markdownify", "--quiet"])
    from markdownify import markdownify as md  # type: ignore

logger = logging.getLogger("archgraph.ingestion")

# ---------------------------------------------------------------------------
# Domain registry
# ---------------------------------------------------------------------------
DOMAIN_REGISTRY: dict[str, list[str]] = {
    "netflixtechblog.com":               ["WebScale", "Microservices", "HighAvailability"],
    "eng.uber.com":                      ["WebScale", "Microservices", "RealTime"],
    "engineering.fb.com":                ["WebScale", "AIInfra", "MLOps"],
    "medium.com/airbnb-engineering":     ["WebScale", "DataEngineering"],
    "blog.cloudflare.com":               ["WebScale", "EdgeComputing", "Security"],
    "aws.amazon.com/blogs/architecture": ["WebScale", "Cloud", "Serverless"],
    "discord.com/blog":                  ["RealTime", "HighThroughput", "Infrastructure"],
    "slack.engineering":                 ["RealTime", "Infrastructure"],
    "medium.com/pinterest-engineering":  ["Infrastructure", "DataEngineering"],
    "stripe.com/blog/engineering":       ["Finance", "Payments", "Compliance"],
    "medium.com/paypal-tech":            ["Finance", "Payments", "Security"],
    "databricks.com/blog":               ["DataEngineering", "MLOps"],
    "developer.nvidia.com/blog":         ["HardwareCoDesign", "AIInfra"],
    "openai.com/research":               ["AIInfra", "MLOps"],
    "anthropic.com/research":            ["AIInfra", "MLOps"],
    "innovation.philips.com/blog":       ["MedTech", "IoMT", "Compliance"],
    "oracle.com/health/blog":            ["MedTech", "Compliance", "HIPAA"],
    "veeva.com/blog":                    ["MedTech", "Compliance", "Regulatory"],
    # Indian tech — community-requested
    "engineering.razorpay.com":          ["Finance", "Payments", "WebScale"],
    "blog.zomato.com":                   ["WebScale", "DataEngineering"],
    "tech.flipkart.com":                 ["WebScale", "DataEngineering"],
    "blog.cred.club/engineering":        ["Finance", "Security"],
}

_NOISE_PATTERNS = re.compile(
    r"(?i)("
    r"we('re| are) hiring|join our team|open positions|careers at \w+"
    r"|subscribe to (our|the) newsletter|sign up for updates"
    r"|follow us on (twitter|linkedin|instagram|facebook)"
    r"|upcoming (event|conference|webinar|summit)"
    r"|written by|about the author|author bio"
    r"|share this (post|article)|tweet this"
    r"|©\s?\d{4}|all rights reserved"
    r"|cookie (policy|consent|settings)"
    r"|related (posts?|articles?)|you (might|may) also like"
    r")"
)

_NOISE_TAGS = [
    "nav", "header", "footer", "aside",
    "script", "style", "noscript", "iframe",
    ".cookie-banner", ".newsletter-signup", ".author-bio",
    ".social-share", ".related-posts", ".ad", ".advertisement",
]

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class RawArticle:
    url: str
    html: str
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status_code: int = 200


@dataclass
class SanitizedArticle:
    url: str
    domain_tags: list[str]
    markdown: str
    content_hash: str
    fetched_at: datetime
    title: str = ""
    char_count: int = 0

    def is_empty(self) -> bool:
        return self.char_count < 200

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "domain_tags": self.domain_tags,
            "markdown": self.markdown,
            "content_hash": self.content_hash,
            "fetched_at": self.fetched_at.isoformat(),
            "char_count": self.char_count,
        }


# ---------------------------------------------------------------------------
# Robots.txt checker (cached per domain)
# ---------------------------------------------------------------------------
class RobotsCache:
    def __init__(self) -> None:
        self._cache: dict[str, RobotFileParser] = {}

    def is_allowed(self, url: str, user_agent: str = "*") -> bool:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        if base not in self._cache:
            rp = RobotFileParser()
            rp.set_url(urljoin(base, "/robots.txt"))
            try:
                rp.read()
            except Exception:
                # If robots.txt can't be fetched, assume allowed
                return True
            self._cache[base] = rp
        return self._cache[base].can_fetch(user_agent, url)


_robots = RobotsCache()


# ---------------------------------------------------------------------------
# Async fetcher
# ---------------------------------------------------------------------------
class ArticleFetcher:
    """Async fetch with aiohttp; Playwright fallback for JS-heavy pages."""

    TIMEOUT = aiohttp.ClientTimeout(total=25)

    async def fetch(self, url: str) -> RawArticle:
        if not _robots.is_allowed(url, _HEADERS["User-Agent"]):
            logger.warning("robots.txt disallows: %s — skipping.", url)
            return RawArticle(url=url, html="", status_code=403)

        logger.info("Fetching (aiohttp): %s", url)
        try:
            async with aiohttp.ClientSession(
                headers=_HEADERS, timeout=self.TIMEOUT
            ) as session:
                async with session.get(url, allow_redirects=True) as resp:
                    if resp.status == 200:
                        text = await resp.text(errors="replace")
                        if len(text) > 500:
                            return RawArticle(url=url, html=text, status_code=200)
                    logger.warning(
                        "aiohttp status %s or thin body; falling back to Playwright.", resp.status
                    )
        except Exception as exc:
            logger.warning("aiohttp failed (%s); falling back to Playwright.", exc)

        return await asyncio.to_thread(self._fetch_playwright, url)

    def _fetch_playwright(self, url: str) -> RawArticle:
        """Sync Playwright in a thread — handles JS-rendered pages."""
        try:
            from playwright.sync_api import sync_playwright  # type: ignore
        except ImportError:
            logger.error("Playwright not installed. Run: pip install playwright && playwright install chromium")
            return RawArticle(url=url, html="", status_code=0)

        logger.info("Fetching (Playwright): %s", url)
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=_HEADERS["User-Agent"])
            page = context.new_page()
            try:
                page.goto(url, wait_until="networkidle", timeout=30_000)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(1.5)
                html = page.content()
                return RawArticle(url=url, html=html)
            except Exception as exc:
                logger.error("Playwright failed for %s: %s", url, exc)
                return RawArticle(url=url, html="", status_code=0)
            finally:
                browser.close()

    async def fetch_batch(self, urls: list[str], concurrency: int = 5) -> list[RawArticle]:
        """Fetch multiple URLs concurrently, capped at `concurrency`."""
        semaphore = asyncio.Semaphore(concurrency)

        async def _limited(url: str) -> RawArticle:
            async with semaphore:
                return await self.fetch(url)

        return await asyncio.gather(*[_limited(u) for u in urls])


# ---------------------------------------------------------------------------
# Sanitizer
# ---------------------------------------------------------------------------
class ArticleSanitizer:
    """Strips noise, extracts main content, converts to clean Markdown."""

    def sanitize(self, raw: RawArticle, domain_tags: list[str]) -> SanitizedArticle:
        if not raw.html:
            return self._empty(raw, domain_tags)

        soup = BeautifulSoup(raw.html, "html.parser")

        for selector in _NOISE_TAGS:
            for tag in soup.select(selector):
                tag.decompose()

        title = ""
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)
        elif soup.title:
            title = soup.title.get_text(strip=True)

        main = (
            soup.find("article")
            or soup.find("main")
            or soup.find(id=re.compile(r"(content|post|article)", re.I))
            or soup.find(class_=re.compile(r"(content|post|article|entry)", re.I))
            or soup.body
            or soup
        )

        raw_md: str = md(
            str(main),
            heading_style="ATX",
            bullets="-",
            strip=["a"],
        )

        clean_lines = [
            line for line in raw_md.splitlines()
            if not _NOISE_PATTERNS.search(line)
        ]
        markdown = re.sub(r"\n{3,}", "\n\n", "\n".join(clean_lines)).strip()
        content_hash = hashlib.sha256(markdown.encode()).hexdigest()

        article = SanitizedArticle(
            url=raw.url,
            domain_tags=domain_tags,
            markdown=markdown,
            content_hash=content_hash,
            fetched_at=raw.fetched_at,
            title=title,
            char_count=len(markdown),
        )

        if article.is_empty():
            logger.warning("Content too thin after sanitization: %s", raw.url)

        logger.info(
            "Sanitized '%s' | tags=%s | chars=%d | hash=%s…",
            title or raw.url, domain_tags, article.char_count, content_hash[:12],
        )
        return article

    def _empty(self, raw: RawArticle, domain_tags: list[str]) -> SanitizedArticle:
        return SanitizedArticle(
            url=raw.url,
            domain_tags=domain_tags,
            markdown="",
            content_hash="",
            fetched_at=raw.fetched_at,
        )


# ---------------------------------------------------------------------------
# Domain router
# ---------------------------------------------------------------------------
def resolve_domain_tags(url: str) -> list[str]:
    for domain, tags in DOMAIN_REGISTRY.items():
        if domain in url:
            return tags
    logger.warning("URL not in domain registry: %s", url)
    return ["Unknown"]


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
class IngestionPipeline:
    """
    Orchestrates: Fetch (async) → Domain Route → Sanitize → Return articles.
    """

    def __init__(self, concurrency: int = 5) -> None:
        self.fetcher = ArticleFetcher()
        self.sanitizer = ArticleSanitizer()
        self.concurrency = concurrency
        self._zero_byte_streak: dict[str, int] = {}

    async def ingest(self, url: str) -> Optional[SanitizedArticle]:
        raw = await self.fetcher.fetch(url)

        if not raw.html:
            streak = self._zero_byte_streak.get(url, 0) + 1
            self._zero_byte_streak[url] = streak
            if streak >= 2:
                logger.error(
                    "ALERT: Zero-byte for '%s' on %d consecutive attempts — isolating target.",
                    url, streak,
                )
            return None
        self._zero_byte_streak[url] = 0

        domain_tags = resolve_domain_tags(url)
        article = self.sanitizer.sanitize(raw, domain_tags)
        return article if not article.is_empty() else None

    async def ingest_batch(self, urls: list[str]) -> list[SanitizedArticle]:
        semaphore = asyncio.Semaphore(self.concurrency)

        async def _limited(url: str) -> Optional[SanitizedArticle]:
            async with semaphore:
                return await self.ingest(url)

        results_raw = await asyncio.gather(*[_limited(u) for u in urls])
        results = [r for r in results_raw if r is not None]
        logger.info("Batch done: %d/%d articles ingested.", len(results), len(urls))
        return results
