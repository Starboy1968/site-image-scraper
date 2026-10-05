# site-image-scraper

Crawl a site, scroll every page to trigger lazy-loaded images, and download all of them.

Most image scrapers only read `<img src>` from static HTML and miss everything that loads on scroll. This one drives a real Chromium browser, scrolls to the bottom of each page, then collects:

- `<img src>` and every URL in `srcset`
- CSS `background-image` on any element
- same-domain links, to keep crawling

Files are saved under a short hash of the source URL, so duplicates collapse and filenames never collide.

## Install

```bash
pip install -r requirements.txt
playwright install chromium
```

## Usage

```bash
python scrape_images.py https://example.com
python scrape_images.py https://example.com --max-pages 50 --out ./imgs --delay 2
```

| Flag | Default | Meaning |
|---|---|---|
| `--out` | `./scraped_images` | Output folder |
| `--max-pages` | `25` | Page cap for the crawl |
| `--delay` | `1.0` | Seconds between page loads |

## Use it responsibly

Only scrape sites you have the right to copy from. Check the site's terms and `robots.txt`, keep the delay polite, and respect the copyright on what you download.

## License

MIT
