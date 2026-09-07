"""User-triggered public documentation intake. The agent cannot fetch arbitrary URLs."""
from urllib.parse import urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup

ALLOWED_HOSTS = {"strandsagents.com", "docs.ollama.com", "ollama.com", "docs.python.org", "docs.aws.amazon.com"}


def validate_fetch_url(url: str) -> str:
    p = urlsplit(url)
    if p.scheme != "https" or p.hostname not in ALLOWED_HOSTS or p.username or p.password or p.port not in {None, 443}:
        raise ValueError("Fetch supports HTTPS official docs on: " + ", ".join(sorted(ALLOWED_HOSTS)))
    return url


def fetch_source(url: str) -> dict:
    validate_fetch_url(url)
    with httpx.Client(timeout=15, follow_redirects=False, trust_env=False) as client:
        for _ in range(4):
            with client.stream("GET", url, headers={"User-Agent": "EvidenceDesk/0.1 public-document-review"}) as response:
                if response.is_redirect:
                    url = validate_fetch_url(urljoin(url, response.headers["location"]))
                    continue
                response.raise_for_status()
                if "text/html" not in response.headers.get("content-type", ""):
                    raise ValueError("Only public HTML documentation is supported by this importer.")
                chunks, size = [], 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > 2_000_000:
                        raise ValueError("Source exceeds the 2 MB intake limit.")
                    chunks.append(chunk)
                soup = BeautifulSoup(b"".join(chunks), "html.parser")
                title = soup.title.get_text(" ", strip=True) if soup.title else url
                root = soup.find("main") or soup.find("article") or soup.body or soup
                for el in root.select("script,style,nav,header,footer,aside,button,form,svg"):
                    el.decompose()
                paragraphs = [p.get_text(" ", strip=True) for p in root.select("p,li")]
                unique = list(dict.fromkeys(p for p in paragraphs if 30 <= len(p) <= 1800))
                text = "\n\n".join(unique)
                truncated = len(text) > 30000
                if truncated:
                    kept, length = [], 0
                    for paragraph in unique:
                        if length + len(paragraph) + 2 > 30000:
                            break
                        kept.append(paragraph)
                        length += len(paragraph) + 2
                    text = "\n\n".join(kept)
                if len(text) < 20:
                    raise ValueError("No readable documentation paragraphs found. Paste a source excerpt instead.")
                return {"title": title[:200], "url": url, "text": text, "truncated": truncated,
                        "intake_note": "Normalized paragraph excerpt; code blocks/tables/layout omitted. Confirm relevant context in the original page."}
    raise ValueError("Too many redirects.")
