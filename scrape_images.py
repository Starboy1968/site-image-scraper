"""
Crawl a site, scroll each page to trigger lazy-loads, download all images.

Usage:
    python scrape_images.py https://example.com
    python scrape_images.py https://example.com --max-pages 50 --out ./imgs
"""
import argparse
import asyncio
import hashlib
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag

import httpx
from playwright.async_api import async_playwright


def same_host(a: str, b: str) -> bool:
    return urlparse(a).netloc == urlparse(b).netloc


def safe_name(url: str) -> str:
    path = urlparse(url).path
    ext = Path(path).suffix.lower() or ".img"
    if ext not in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", ".avif"}:
        ext = ".img"
    h = hashlib.md5(url.encode()).hexdigest()[:12]
    return f"{h}{ext}"


async def scroll_to_bottom(page):
    prev = 0
    for _ in range(20):
        await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
        await page.wait_for_timeout(800)
        h = await page.evaluate("document.body.scrollHeight")
        if h == prev:
            break
        prev = h


async def extract(page, base_url: str):
    imgs = await page.evaluate("""
        () => {
            const out = new Set();
            document.querySelectorAll('img').forEach(i => {
                if (i.src) out.add(i.src);
                if (i.srcset) i.srcset.split(',').forEach(s => out.add(s.trim().split(' ')[0]));
            });
            document.querySelectorAll('*').forEach(el => {
                const bg = getComputedStyle(el).backgroundImage;
                const m = bg && bg.match(/url\\(["']?(.+?)["']?\\)/);
                if (m) out.add(m[1]);
            });
            return [...out];
        }
    """)
    links = await page.evaluate("() => [...document.querySelectorAll('a[href]')].map(a => a.href)")
    return (
        {urljoin(base_url, u) for u in imgs if u and not u.startswith('data:')},
        {urldefrag(urljoin(base_url, l))[0] for l in links},
    )


async def crawl(start: str, out_dir: Path, max_pages: int, delay: float):
    out_dir.mkdir(parents=True, exist_ok=True)
    seen_pages, seen_imgs, queue = set(), set(), [start]

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context()
        page = await ctx.new_page()

        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as http:
            while queue and len(seen_pages) < max_pages:
                url = queue.pop(0)
                if url in seen_pages or not same_host(url, start):
                    continue
                seen_pages.add(url)
                print(f"[{len(seen_pages)}/{max_pages}] {url}")
                try:
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                    await scroll_to_bottom(page)
                    imgs, links = await extract(page, url)
                except Exception as e:
                    print(f"  skip: {e}")
                    continue

                for img in imgs - seen_imgs:
                    seen_imgs.add(img)
                    try:
                        r = await http.get(img)
                        if r.status_code == 200:
                            (out_dir / safe_name(img)).write_bytes(r.content)
                    except Exception as e:
                        print(f"  img fail {img}: {e}")

                for link in links:
                    if link not in seen_pages and same_host(link, start):
                        queue.append(link)

                if delay > 0:
                    await asyncio.sleep(delay)

        await browser.close()

    print(f"\nDone. {len(seen_imgs)} images -> {out_dir}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--out", default="./scraped_images")
    ap.add_argument("--max-pages", type=int, default=25)
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between page loads")
    args = ap.parse_args()
    asyncio.run(crawl(args.url, Path(args.out), args.max_pages, args.delay))
