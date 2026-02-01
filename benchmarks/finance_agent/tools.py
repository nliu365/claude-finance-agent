import json
import os
import re
from html.parser import HTMLParser
from typing import Dict, List, Optional

import requests


class _HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._chunks = []

    def handle_data(self, data):
        text = data.strip()
        if text:
            self._chunks.append(text)

    def get_text(self) -> str:
        return " ".join(self._chunks)


def parse_html_page(html: str, max_chars: int = 4000) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(html)
    text = parser.get_text()
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


def google_web_search(query: str, api_key: Optional[str] = None, num_results: int = 5) -> List[Dict]:
    key = api_key or os.getenv("SERPAPI_API_KEY")
    if not key:
        raise RuntimeError("SERPAPI_API_KEY not set")
    params = {
        "engine": "google",
        "q": query,
        "num": num_results,
        "api_key": key,
    }
    resp = requests.get("https://serpapi.com/search.json", params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    results = []
    for item in data.get("organic_results", []):
        results.append({
            "title": item.get("title"),
            "link": item.get("link"),
            "snippet": item.get("snippet"),
        })
    return results


def edgar_search(query: str, api_key: Optional[str] = None, size: int = 5) -> Dict:
    key = api_key or os.getenv("SEC_API_KEY")
    if not key:
        raise RuntimeError("SEC_API_KEY not set")
    # SEC-API full-text search endpoint
    payload = {
        "query": {"query_string": {"query": query}},
        "from": 0,
        "size": size,
        "sort": [{"filedAt": {"order": "desc"}}],
    }
    headers = {"Authorization": key, "Content-Type": "application/json"}
    resp = requests.post("https://api.sec-api.io/full-text-search", headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_url(url: str, user_agent: Optional[str] = None, timeout: int = 30) -> str:
    headers = {}
    if user_agent:
        headers["User-Agent"] = user_agent
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.text
