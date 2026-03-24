#!/usr/bin/env python3
import argparse
import html
import json
import re
import time
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from bs4 import BeautifulSoup
from curl_cffi import requests as curl_requests


ERROR_INVALID_URL = "invalid_url"
ERROR_BLOCKED_403 = "blocked_403"
ERROR_TIMEOUT = "timeout"
ERROR_NO_CONTENT = "no_content"


class WechatArticleFetcher:
    def __init__(self, timeout: int = 20, max_retries: int = 3, retry_delay: float = 1.0) -> None:
        self.timeout = timeout
        self.max_retries = max(1, max_retries)
        self.retry_delay = max(0.0, retry_delay)
        # 维持会话可以重用 cookies，被当作同一个正常用户的概率更高
        self.session = curl_requests.Session(impersonate="chrome124", timeout=self.timeout)
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0 Safari/537.36 MicroMessenger/8.0",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        })

    @staticmethod
    def is_public_wechat_article(url: str) -> bool:
        parsed = urlparse(url)
        return parsed.scheme in {"http", "https"} and parsed.hostname == "mp.weixin.qq.com" and parsed.path.startswith("/s")

    @staticmethod
    def strip_tracking_params(url: str) -> str:
        parsed = urlparse(url)
        filtered = [
            (k, v)
            for k, v in parse_qsl(parsed.query, keep_blank_values=True)
            if k not in {"scene", "utm_source", "utm_medium", "utm_campaign"}
        ]
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, urlencode(filtered), parsed.fragment))

    def _fetch_html_once(self, url: str) -> tuple[str | None, int | None, str | None]:
        try:
            response = self.session.get(url)
            return response.text, response.status_code, None
        except Exception as exc:
            return None, None, str(exc)

    def fetch(self, url: str) -> dict:
        if not self.is_public_wechat_article(url):
            return {
                "error": ERROR_INVALID_URL,
                "message": "URL must be a public mp.weixin.qq.com/s article.",
                "source_url": url,
            }

        clean_url = self.strip_tracking_params(url)
        page_html = None
        status = None
        attempt_logs = []
        for attempt in range(1, self.max_retries + 1):
            page_html, status, error_text = self._fetch_html_once(clean_url)
            attempt_logs.append({"attempt": attempt, "status": status, "error": error_text})
            should_retry = page_html is None and status != 403 and attempt < self.max_retries
            if not should_retry:
                break
            time.sleep(self.retry_delay * attempt)
        strategy = "curl_cffi"
        logs = {"http_status": status, "attempts": attempt_logs}
        if not page_html:
            error = ERROR_BLOCKED_403 if status == 403 else ERROR_TIMEOUT
            return {
                "error": error,
                "message": "Failed to fetch article HTML.",
                "source_url": clean_url,
                "strategy": strategy,
                "logs": logs,
            }

        return {
            "page_html": page_html,
            "status": status,
            "source_url": clean_url,
            "strategy": strategy,
            "logs": logs,
        }


class WechatArticleParser:
    @staticmethod
    def _extract_first(pattern: str, text: str, flags: int = re.I | re.S) -> str:
        match = re.search(pattern, text, flags)
        return match.group(1).strip() if match else ""

    def parse(self, page_html: str) -> dict:
        soup = BeautifulSoup(page_html, "html.parser")
        title_node = soup.find(id="activity-name")
        author_node = soup.find(id="js_name")
        title = title_node.get_text(" ", strip=True) if title_node else ""
        author = author_node.get_text(" ", strip=True) if author_node else ""

        if not title:
            title_meta = soup.find("meta", attrs={"property": "og:title"})
            title = title_meta.get("content", "").strip() if title_meta else ""
        if not author:
            author_meta = soup.find("meta", attrs={"name": "author"})
            author = author_meta.get("content", "").strip() if author_meta else ""

        pub_time = ""
        for attrs in ({"property": "article:published_time"}, {"property": "og:updated_time"}):
            meta = soup.find("meta", attrs=attrs)
            if meta and meta.get("content"):
                pub_time = meta["content"].strip()
                break
        if not pub_time:
            timestamp = self._extract_first(r'var\s+ct\s*=\s*"(\d{10})"', page_html, re.I)
            if timestamp:
                pub_time = datetime.fromtimestamp(int(timestamp), tz=timezone.utc).isoformat()

        content_node = soup.find(id="js_content")
        content = content_node.get_text("\n", strip=True) if content_node else ""
        content = html.unescape(content)
        content = re.sub(r"\n{3,}", "\n\n", content).strip()

        return {
            "title": html.unescape(title.strip()),
            "pub_time": pub_time,
            "author": html.unescape(author.strip()),
            "content": content,
        }


def main() -> int:
    cli = argparse.ArgumentParser(description="Read WeChat article into structured JSON.")
    cli.add_argument("url", help="Public article URL like https://mp.weixin.qq.com/s/...")
    cli.add_argument("--timeout", type=int, default=20)
    cli.add_argument("--max-retries", type=int, default=3)
    cli.add_argument("--retry-delay", type=float, default=1.0)
    args = cli.parse_args()

    fetcher = WechatArticleFetcher(timeout=args.timeout, max_retries=args.max_retries, retry_delay=args.retry_delay)
    fetched = fetcher.fetch(args.url)
    if "error" in fetched:
        print(json.dumps(fetched, ensure_ascii=False, indent=2))
        return 1

    parser = WechatArticleParser()
    parsed = parser.parse(fetched["page_html"])
    if not parsed["content"]:
        result = {
            "error": ERROR_BLOCKED_403 if fetched["status"] == 403 else ERROR_NO_CONTENT,
            "message": "Fetched page but could not find #js_content.",
            "source_url": fetched["source_url"],
            "strategy": fetched["strategy"],
            "logs": fetched["logs"],
            "title": parsed["title"],
            "author": parsed["author"],
            "pub_time": parsed["pub_time"],
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    result = {
        "title": parsed["title"],
        "pub_time": parsed["pub_time"],
        "author": parsed["author"],
        "content": parsed["content"],
        "source_url": fetched["source_url"],
        "strategy": fetched["strategy"],
        "logs": fetched["logs"],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
