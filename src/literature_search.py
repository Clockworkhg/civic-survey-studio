"""学术文献检索模块。

通过免费学术 API 检索文献，无需 API Key。
优先使用 Semantic Scholar（免费额度最好，提供摘要），
结果不足时补充 OpenAlex 和 CrossRef。

使用示例:
    from src.literature_search import search_papers, PaperRecord

    papers = search_papers("public service satisfaction citizen", max_results=15)
    for p in papers:
        print(f"{p.apa_citation()}")
"""

from __future__ import annotations

import json
import logging
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ================================================================
# 常量
# ================================================================

_S2_BASE = "https://api.semanticscholar.org/graph/v1"
_S2_FIELDS = "title,authors,year,externalIds,abstract,url,venue,publicationDate,openAccessPdf"
_OPENALEX_BASE = "https://api.openalex.org"
_CROSSREF_BASE = "https://api.crossref.org"

# 速率限制（秒）
_S2_INTERVAL = 1.05       # 未认证：~1 req/s
_OPENALEX_INTERVAL = 0.12  # 礼貌池：~10 req/s（提供 email 最优）
_CROSSREF_INTERVAL = 0.22  # 匿名池：~5 req/s

_MAX_RETRIES = 3
_BACKOFF_BASE = 2.0
_REQUEST_TIMEOUT = 25.0

_USER_AGENT = (
    "civic-survey-studio/0.1.0 "
    "(mailto:research@example.com)"
)


# ================================================================
# 数据类
# ================================================================

@dataclass
class PaperRecord:
    """单篇学术论文的结构化记录。"""

    title: str
    authors: List[str]
    year: Optional[int]
    doi: Optional[str]
    abstract: Optional[str]
    source: str          # "semantic_scholar" | "openalex" | "crossref"
    url: Optional[str] = None
    venue: Optional[str] = None
    citation_count: Optional[int] = None

    def apa_citation(self) -> str:
        """生成 APA 第7版引注字符串。"""
        if self.authors:
            if len(self.authors) == 1:
                author_str = self.authors[0]
            elif len(self.authors) == 2:
                author_str = f"{self.authors[0]} & {self.authors[1]}"
            else:
                author_str = f"{self.authors[0]} et al."
        else:
            author_str = "Unknown Author"

        year_str = f"({self.year})" if self.year else "(n.d.)"
        citation = f"{author_str} {year_str}. {self.title}."

        if self.venue:
            citation += f" *{self.venue}*."

        if self.doi:
            citation += f" https://doi.org/{self.doi}"

        return citation

    def to_dict(self) -> Dict[str, Any]:
        """转为字典（用于 JSON 序列化和 LLM prompt 构建）。"""
        return {
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "doi": self.doi,
            "abstract": self.abstract,
            "source": self.source,
            "url": self.url,
            "venue": self.venue,
            "apa_citation": self.apa_citation(),
        }


# ================================================================
# 工具函数
# ================================================================

def _safe_get(obj: Any, *keys: str, default: Any = None) -> Any:
    """安全访问嵌套字典。"""
    for key in keys:
        if isinstance(obj, dict):
            obj = obj.get(key, default)
        else:
            return default
    return obj


def _http_get(url: str, timeout: float = _REQUEST_TIMEOUT) -> bytes:
    """发送 HTTP GET 请求，自动重试和退避。"""
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    last_error = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < _MAX_RETRIES:
                wait = _BACKOFF_BASE ** (attempt + 1)
                logger.debug(f"HTTP 429, retrying in {wait:.1f}s (attempt {attempt + 1}/{_MAX_RETRIES})")
                time.sleep(wait)
                last_error = e
                continue
            raise
        except (urllib.error.URLError, OSError) as e:
            if attempt < _MAX_RETRIES:
                wait = _BACKOFF_BASE ** (attempt + 1)
                logger.debug(f"Network error: {e}, retrying in {wait:.1f}s")
                time.sleep(wait)
                last_error = e
                continue
            raise
    raise last_error  # type: ignore[misc]


def _normalize_title(title: str) -> str:
    """归一化标题用于去重比较。"""
    return re.sub(r'[^a-z0-9\s]', '', title.lower()).strip()


# ================================================================
# 速率限制器
# ================================================================

class _RateLimiter:
    """简单的令牌桶式速率限制器。"""

    def __init__(self, interval: float):
        self._interval = interval
        self._last_call: float = 0.0

    def wait(self):
        now = time.monotonic()
        elapsed = now - self._last_call
        if elapsed < self._interval:
            time.sleep(self._interval - elapsed)
        self._last_call = time.monotonic()


# ================================================================
# Semantic Scholar 搜索
# ================================================================

_s2_limiter = _RateLimiter(_S2_INTERVAL)


def _search_semantic_scholar(
    keywords: str,
    limit: int,
    year_from: Optional[int],
    year_to: Optional[int],
    timeout: float,
) -> List[PaperRecord]:
    """通过 Semantic Scholar API 搜索论文。"""
    params: Dict[str, str] = {
        "query": keywords,
        "limit": str(min(limit, 100)),
        "fields": _S2_FIELDS,
    }
    if year_from:
        params["year"] = f"{year_from}-" + (str(year_to) if year_to else "")
    elif year_to:
        params["year"] = f"1900-{year_to}"

    qs = urllib.parse.urlencode(params)
    url = f"{_S2_BASE}/paper/search?{qs}"

    _s2_limiter.wait()
    try:
        body = _http_get(url, timeout=timeout)
        data = json.loads(body)
    except Exception as e:
        logger.warning(f"Semantic Scholar search failed: {e}")
        return []

    papers: List[PaperRecord] = []
    for item in data.get("data", []):
        try:
            paper = PaperRecord(
                title=str(item.get("title", "")).strip(),
                authors=[a.get("name", "") for a in item.get("authors", [])],
                year=_safe_int(item.get("year")),
                doi=_safe_get(item, "externalIds", "DOI") or None,
                abstract=str(item.get("abstract", "")).strip() or None,
                source="semantic_scholar",
                url=item.get("url") or None,
                venue=_safe_get(item, "venue", "name") or item.get("venue") or None,
                citation_count=_safe_int(item.get("citationCount")),
            )
            if paper.title and (paper.abstract or paper.doi):
                papers.append(paper)
        except Exception as e:
            logger.debug(f"Skipping malformed S2 record: {e}")
            continue

    logger.info(f"Semantic Scholar: found {len(papers)} papers")
    return papers


def _safe_int(value: Any) -> Optional[int]:
    """安全转为 int，失败返回 None。"""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


# ================================================================
# OpenAlex 搜索
# ================================================================

_openalex_limiter = _RateLimiter(_OPENALEX_INTERVAL)


def _search_openalex(
    keywords: str,
    limit: int,
    year_from: Optional[int],
    year_to: Optional[int],
    timeout: float,
) -> List[PaperRecord]:
    """通过 OpenAlex API 搜索论文（作为补充数据源）。"""
    params: Dict[str, str] = {
        "search": keywords,
        "per-page": str(min(limit, 50)),
        "select": "id,title,authorships,publication_year,doi,primary_location,abstract_inverted_index,cited_by_count",
    }
    if year_from:
        params["filter"] = f"from_publication_date:{year_from}-01-01"
        if year_to:
            params["filter"] += f",to_publication_date:{year_to}-12-31"
    elif year_to:
        params["filter"] = f"to_publication_date:{year_to}-12-31"

    qs = urllib.parse.urlencode(params)
    url = f"{_OPENALEX_BASE}/works?{qs}"

    _openalex_limiter.wait()
    try:
        body = _http_get(url, timeout=timeout)
        data = json.loads(body)
    except Exception as e:
        logger.warning(f"OpenAlex search failed: {e}")
        return []

    papers: List[PaperRecord] = []
    for item in data.get("results", []):
        try:
            abstract = _extract_openalex_abstract(item.get("abstract_inverted_index"))
            paper = PaperRecord(
                title=str(item.get("title", "")).strip(),
                authors=[
                    a.get("author", {}).get("display_name", "")
                    for a in item.get("authorships", [])
                ],
                year=_safe_int(item.get("publication_year")),
                doi=_extract_openalex_doi(item.get("doi")),
                abstract=abstract,
                source="openalex",
                url=item.get("id") or None,
                venue=_extract_openalex_venue(item.get("primary_location")),
                citation_count=_safe_int(item.get("cited_by_count")),
            )
            if paper.title:
                papers.append(paper)
        except Exception as e:
            logger.debug(f"Skipping malformed OpenAlex record: {e}")
            continue

    logger.info(f"OpenAlex: found {len(papers)} papers")
    return papers


def _extract_openalex_doi(doi_url: Optional[str]) -> Optional[str]:
    """从 OpenAlex 的 DOI URL 中提取纯 DOI。"""
    if not doi_url:
        return None
    prefix = "https://doi.org/"
    if doi_url.startswith(prefix):
        return doi_url[len(prefix):]
    return doi_url


def _extract_openalex_venue(primary_location: Optional[Dict]) -> Optional[str]:
    """从 OpenAlex primary_location 中提取期刊/会议名。"""
    if not primary_location or not isinstance(primary_location, dict):
        return None
    source = primary_location.get("source")
    if source and isinstance(source, dict):
        return source.get("display_name") or None
    return None


def _extract_openalex_abstract(inverted_index: Optional[Dict]) -> Optional[str]:
    """将 OpenAlex 的倒排摘要索引还原为文本。"""
    if not inverted_index or not isinstance(inverted_index, dict):
        return None
    try:
        max_pos = 0
        for positions in inverted_index.values():
            if isinstance(positions, list):
                for p in positions:
                    if isinstance(p, (int, float)) and p > max_pos:
                        max_pos = int(p)
        words = [""] * (max_pos + 1)
        for word, positions in inverted_index.items():
            if isinstance(positions, list):
                for p in positions:
                    if isinstance(p, (int, float)) and int(p) <= max_pos:
                        words[int(p)] = word
        return " ".join(words).strip() or None
    except Exception:
        return None


# ================================================================
# CrossRef 搜索
# ================================================================

_crossref_limiter = _RateLimiter(_CROSSREF_INTERVAL)


def _search_crossref(
    keywords: str,
    limit: int,
    year_from: Optional[int],
    year_to: Optional[int],
    timeout: float,
) -> List[PaperRecord]:
    """通过 CrossRef API 搜索论文（作为进一步补充数据源）。"""
    params: Dict[str, str] = {
        "query": keywords,
        "rows": str(min(limit, 50)),
    }
    filter_parts: List[str] = []
    if year_from:
        filter_parts.append(f"from-pub-date:{year_from}-01-01")
    if year_to:
        filter_parts.append(f"until-pub-date:{year_to}-12-31")
    if filter_parts:
        params["filter"] = ",".join(filter_parts)

    qs = urllib.parse.urlencode(params)
    url = f"{_CROSSREF_BASE}/works?{qs}"

    _crossref_limiter.wait()
    try:
        body = _http_get(url, timeout=timeout)
        data = json.loads(body)
    except Exception as e:
        logger.warning(f"CrossRef search failed: {e}")
        return []

    papers: List[PaperRecord] = []
    items = _safe_get(data, "message", "items", default=[])
    if not isinstance(items, list):
        return papers

    for item in items:
        try:
            if not isinstance(item, dict):
                continue
            title_list = item.get("title", [])
            title = title_list[0] if title_list else ""
            if not title:
                continue

            author_list = item.get("author", [])
            authors = []
            for a in author_list:
                if isinstance(a, dict):
                    given = a.get("given", "")
                    family = a.get("family", "")
                    name = f"{family}, {given}" if family else given
                    if name:
                        authors.append(name)

            year = _extract_crossref_year(item)
            doi = item.get("DOI") or None
            venue = None
            container = item.get("container-title", [])
            if container and isinstance(container, list):
                venue = container[0] or None

            # CrossRef 通常不提供摘要，但 title 已足够
            abstract = item.get("abstract") or None

            paper = PaperRecord(
                title=str(title).strip(),
                authors=authors,
                year=year,
                doi=doi,
                abstract=str(abstract).strip() if abstract else None,
                source="crossref",
                url=f"https://doi.org/{doi}" if doi else None,
                venue=venue,
                citation_count=None,
            )
            if paper.title:
                papers.append(paper)
        except Exception as e:
            logger.debug(f"Skipping malformed CrossRef record: {e}")
            continue

    logger.info(f"CrossRef: found {len(papers)} papers")
    return papers


def _extract_crossref_year(item: Dict) -> Optional[int]:
    """从 CrossRef 记录中提取发表年份。"""
    issued = item.get("issued", {})
    if isinstance(issued, dict):
        date_parts = issued.get("date-parts", [])
        if date_parts and isinstance(date_parts, list):
            first = date_parts[0]
            if isinstance(first, list) and first:
                return _safe_int(first[0])
    # 回退
    for key in ("published-print", "published-online", "created"):
        alt = item.get(key, {})
        if isinstance(alt, dict):
            dp = alt.get("date-parts", [])
            if dp and isinstance(dp, list) and dp[0]:
                if isinstance(dp[0], list) and dp[0]:
                    return _safe_int(dp[0][0])
    return None


# ================================================================
# 去重
# ================================================================

def _deduplicate_papers(papers: List[PaperRecord]) -> List[PaperRecord]:
    """去除跨数据源重复的论文（基于 DOI 或归一化标题）。

    策略：
      1. 主键：DOI（不区分大小写，归一化前缀）
      2. 次键：归一化标题
      3. 重复时优先保留：有摘要 > 作者全 > Semantic Scholar 来源

    使用字典聚合，O(n) 时间复杂度。
    """
    best: Dict[str, PaperRecord] = {}
    order: List[str] = []  # 保持首次出现顺序

    for paper in papers:
        # 主键：归一化 DOI
        key = ""
        if paper.doi:
            key = re.sub(r'^https?://(dx\.)?doi\.org/', '', paper.doi.strip().lower())
        # 次键：归一化标题
        if not key:
            key = f"title:{_normalize_title(paper.title)}"
        if not key:
            continue

        if key in best:
            if _is_better(paper, best[key]):
                best[key] = paper
        else:
            best[key] = paper
            order.append(key)

    return [best[k] for k in order]


def _is_better(new_p: PaperRecord, old_p: PaperRecord) -> bool:
    """判断 new_p 是否比 old_p 更值得保留。"""
    if bool(new_p.abstract) != bool(old_p.abstract):
        return bool(new_p.abstract)
    if len(new_p.authors) != len(old_p.authors):
        return len(new_p.authors) > len(old_p.authors)
    source_rank = {"semantic_scholar": 3, "openalex": 2, "crossref": 1}
    return source_rank.get(new_p.source, 0) > source_rank.get(old_p.source, 0)


# ================================================================
# 主搜索入口
# ================================================================

def search_papers(
    keywords: str,
    max_results: int = 15,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    timeout: float = 30.0,
) -> List[PaperRecord]:
    """搜索学术论文，返回去重并排序的 PaperRecord 列表。

    搜索策略：
      1. 优先搜索 Semantic Scholar（元数据最丰富）
      2. 如果结果不足 max_results，补充 OpenAlex
      3. 如果仍不足，补充 CrossRef
      4. 去重后按年份降序排列

    Args:
        keywords: 搜索关键词（英文效果最佳，中文关键词也会尝试验证）
        max_results: 最大返回论文数（5-50）
        year_from: 最早发表年份（含），None 表示不限
        year_to: 最晚发表年份（含），None 表示不限
        timeout: 单次 HTTP 请求超时（秒）

    Returns:
        去重后的 PaperRecord 列表，按年份降序排列。
        如果所有 API 均不可用，返回空列表。
    """
    if not keywords or not keywords.strip():
        logger.warning("Empty keywords provided to search_papers")
        return []

    # 对中文关键词进行简单翻译提示（实际搜索仍用原始关键词尝试）
    all_papers: List[PaperRecord] = []

    # ── 主数据源：Semantic Scholar ──
    s2_papers = _search_semantic_scholar(keywords, max_results, year_from, year_to, timeout)
    all_papers.extend(s2_papers)

    # ── 补充数据源 1：OpenAlex（如果 S2 结果不足）──
    if len(s2_papers) < max_results:
        remaining = max_results - len(s2_papers)
        oa_papers = _search_openalex(keywords, remaining, year_from, year_to, timeout)
        all_papers.extend(oa_papers)

    # ── 补充数据源 2：CrossRef（如果仍不足）──
    if len(all_papers) < max_results:
        remaining = max_results - len(all_papers)
        cr_papers = _search_crossref(keywords, remaining, year_from, year_to, timeout)
        all_papers.extend(cr_papers)

    # ── 去重 ──
    unique = _deduplicate_papers(all_papers)

    # ── 排序：有摘要的优先，同组内按年份降序 ──
    unique.sort(key=lambda p: (1 if p.abstract else 0, p.year or 0), reverse=True)

    # ── 截断到 max_results ──
    result = unique[:max_results]

    logger.info(
        f"search_papers: total_found={len(all_papers)}, "
        f"unique={len(unique)}, returned={len(result)}, "
        f"s2={len(s2_papers)}, oa={sum(1 for p in all_papers if p.source=='openalex')}, "
        f"cr={sum(1 for p in all_papers if p.source=='crossref')}"
    )

    return result
