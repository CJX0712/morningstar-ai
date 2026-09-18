"""联网搜索工具。

优先使用 SerpAPI（若配置了 SERPAPI_KEY），否则回退到 DuckDuckGo HTML 抓取（无需 Key）。
"""
from __future__ import annotations

import re
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from app.config import settings

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}


def _duckduckgo(query: str, num_results: int = 5) -> str:
    try:
        resp = httpx.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers=_HEADERS,
            timeout=15.0,
        )
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        return f"[搜索失败] {exc}"

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []
    for node in soup.select(".result")[:num_results]:
        title_tag = node.select_one(".result__a")
        snippet_tag = node.select_one(".result__snippet")
        title = title_tag.get_text(strip=True) if title_tag else "(无标题)"
        snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
        results.append(f"- {title}: {snippet}")
    if not results:
        return "未找到相关结果。"
    return "\n".join(results)


def _serpapi(query: str, num_results: int = 5) -> str:
    try:
        resp = httpx.get(
            "https://serpapi.com/search.json",
            params={"q": query, "api_key": settings.serpapi_key, "num": num_results},
            timeout=15.0,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # noqa: BLE001
        return f"[SerpAPI 搜索失败] {exc}"
    organic = data.get("organic_results", [])
    lines = [
        f"- {r.get('title', '')}: {r.get('snippet', '')}"
        for r in organic[:num_results]
    ]
    return "\n".join(lines) if lines else "未找到相关结果。"


def web_search(query: str, num_results: int = 5) -> str:
    """执行联网搜索，返回格式化结果文本。"""
    if settings.serpapi_key:
        return _serpapi(query, num_results)
    return _duckduckgo(query, num_results)
