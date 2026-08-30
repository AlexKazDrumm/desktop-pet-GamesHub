"""Разбор HTML-карточки игры с mygamelist.club."""

from __future__ import annotations

import json
import re
from typing import Any

from bs4 import BeautifulSoup, NavigableString, Tag

from desktop_pet_gameshub.models.game import MGLGameData

MGL_BASE_URL = "https://mygamelist.club/game/"

_GARBAGE_LABELS = {
    "home", "about", "support us", "privacy policy", "cookie policy", "terms of use",
    "sign in", "calendar", "community", "reviews", "read", "new!", "help", "login", "logout",
    "повторить", "подписаться", "войти", "выйти",
}

_PLATFORM_ALIASES = {
    "pc": "PC (Microsoft Windows)",
    "windows": "PC (Microsoft Windows)",
    "microsoft windows": "PC (Microsoft Windows)",
    "xbox series": "Xbox Series X|S",
    "xbox series x": "Xbox Series X|S",
    "xbox series x|s": "Xbox Series X|S",
    "xbox one": "Xbox One",
    "ps4": "PlayStation 4",
    "playstation 4": "PlayStation 4",
    "ps5": "PlayStation 5",
    "playstation 5": "PlayStation 5",
    "switch": "Nintendo Switch",
    "nintendo switch": "Nintendo Switch",
    "nintendo switch 2": "Nintendo Switch 2",
}

_LABEL_MAP = {
    "developers": {"разработчик", "разработчики", "developer", "developers"},
    "publishers": {"издатель", "издатели", "publisher", "publishers"},
    "genres": {"жанр", "жанры", "genre", "genres"},
    "platforms": {"платформа", "платформы", "platform", "platforms"},
}

_COLON_RE = re.compile(r"[：:]\s*$")
_SPACE_NORM_RE = re.compile(r"\s+")
_YEAR_RE = re.compile(r"\b(19[5-9]\d|20[0-4]\d|2050)\b")


def _pick_main_container(soup: BeautifulSoup):
    for sel in ["main", "article", "#main", "#content", ".content", ".container", ".container-fluid"]:
        el = soup.select_one(sel)
        if el:
            return el
    return soup.body or soup


def _extract_cover(main) -> str | None:
    for img in main.find_all("img"):
        src = (img.get("src") or "").strip()
        if src and "images.igdb.com" in src and ("cover" in src or "t_cover" in src or "t_thumb" in src):
            return src
    for img in main.find_all("img"):
        src = (img.get("src") or "").strip()
        if "images.igdb.com" in src:
            return src
    for img in main.find_all("img"):
        src = (img.get("src") or "").strip()
        w = int(img.get("width") or 0)
        h = int(img.get("height") or 0)
        if src and (w >= 180 or h >= 180):
            return src
    return None


def _clean_names(items: list[str]) -> list[str]:
    out = []
    for x in items or []:
        t = (x or "").strip()
        if not t:
            continue
        tl = t.lower()
        if any(g in tl for g in _GARBAGE_LABELS):
            continue
        if tl.startswith("reviews"):
            continue
        if len(t) > 200:
            continue
        out.append(t)
    seen = set()
    uniq = []
    for t in out:
        k = t.lower()
        if k in seen:
            continue
        seen.add(k)
        uniq.append(t)
    return uniq


def _normalize_platforms(plats: list[str]) -> list[str]:
    out = [_PLATFORM_ALIASES.get(p.strip().lower(), p.strip()) for p in plats or []]
    seen = set()
    res = []
    for p in out:
        k = p.lower()
        if k in seen:
            continue
        seen.add(k)
        res.append(p)
    return res


def _as_list(x: str | list | None) -> list[str]:
    if x is None:
        return []
    if isinstance(x, list):
        return [str(i) for i in x if i]
    return [str(x)]


def _jsonld_pick(obj: Any, *keys: str) -> list[str]:
    out: list[str] = []
    for k in keys:
        if isinstance(obj, dict) and k in obj and obj[k]:
            val = obj[k]
            if isinstance(val, list):
                for it in val:
                    if isinstance(it, dict) and "name" in it:
                        out.append(str(it["name"]))
                    else:
                        out.extend(_as_list(it))
            elif isinstance(val, dict) and "name" in val:
                out.append(str(val["name"]))
            else:
                out.extend(_as_list(val))
    return _clean_names(out)


def _parse_jsonld_blocks(soup: BeautifulSoup) -> dict[str, list[str]]:
    result = {"genres": [], "platforms": [], "developers": [], "publishers": []}
    buckets: list[Any] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            txt = script.string or script.get_text() or ""
            if not txt.strip():
                continue
            data = json.loads(txt)
        except Exception:
            continue
        buckets.extend(data if isinstance(data, list) else [data])

    for obj in buckets:
        if not isinstance(obj, dict):
            continue
        types = {t.lower() for t in _as_list(obj.get("@type"))}
        if not types or types & {"videogame", "game", "creativework"}:
            result["genres"].extend(_jsonld_pick(obj, "genre", "genres"))
            result["platforms"].extend(_jsonld_pick(obj, "gamePlatform", "operatingSystem", "platform", "gamePlatforms"))
            result["developers"].extend(_jsonld_pick(obj, "developer", "developers", "author", "creator"))
            result["publishers"].extend(_jsonld_pick(obj, "publisher", "publishers"))

        for nested_key in ("item", "mainEntity"):
            nested = obj.get(nested_key)
            if isinstance(nested, dict):
                result["genres"].extend(_jsonld_pick(nested, "genre", "genres"))
                result["platforms"].extend(_jsonld_pick(nested, "gamePlatform", "operatingSystem", "platform", "gamePlatforms"))
                result["developers"].extend(_jsonld_pick(nested, "developer", "developers", "author", "creator"))
                result["publishers"].extend(_jsonld_pick(nested, "publisher", "publishers"))

    result["genres"] = _clean_names(result["genres"])
    result["platforms"] = _normalize_platforms(_clean_names(result["platforms"]))
    result["developers"] = _clean_names(result["developers"])
    result["publishers"] = _clean_names(result["publishers"])
    return result


def _norm_label(text: str) -> str:
    t = (text or "").replace("\xa0", " ")
    t = _SPACE_NORM_RE.sub(" ", t).strip()
    return _COLON_RE.sub("", t).strip().lower()


def _split_values(raw: str | None) -> list[str]:
    if raw is None:
        return []
    return [p for p in (p.strip() for p in re.split(r"[;,]", raw)) if p]


def _text_clean(el: Tag | NavigableString | None) -> str:
    if not el:
        return ""
    t = str(el) if isinstance(el, (str, NavigableString)) else el.get_text(" ", strip=True)
    t = t.replace("\xa0", " ")
    return _SPACE_NORM_RE.sub(" ", t).strip()


def _match_label(label: str) -> str | None:
    for key, variants in _LABEL_MAP.items():
        if label in variants:
            return key
    return None


def _extract_value_nodes_from_li(li: Tag, label_span: Tag) -> list[str]:
    results: list[str] = []

    for sp in li.find_all(["span", "a"], recursive=False):
        if sp is label_span:
            continue
        txt = _text_clean(sp)
        if not txt:
            continue
        links = [a.get_text(" ", strip=True) for a in sp.find_all("a")]
        results.extend(links if links else [txt])

    if not results:
        collected = []
        after_label = False
        for node in li.children:
            if node is label_span:
                after_label = True
                continue
            if not after_label:
                continue
            if isinstance(node, NavigableString):
                t = _text_clean(node)
                if t:
                    collected.append(t)
            elif isinstance(node, Tag):
                if node.name in ("a", "span", "em", "strong"):
                    t = _text_clean(node)
                    if t:
                        collected.append(t)
                links = [a.get_text(" ", strip=True) for a in node.find_all("a")]
                collected.extend(links)
        results.extend(collected)

    out: list[str] = []
    for chunk in results:
        out.extend(_split_values(chunk))
    return _clean_names(out)


def _extract_from_ul_blocks(root: Tag) -> dict[str, list[str]]:
    acc: dict[str, list[str]] = {"developers": [], "publishers": [], "genres": [], "platforms": []}
    for li in root.find_all("li"):
        spans = li.find_all("span", recursive=False)
        if not spans:
            continue

        label_span = next((sp for sp in spans if "text-dimmed" in (sp.get("class") or [])), None)
        if not label_span and ":" in _text_clean(spans[0]):
            label_span = spans[0]
        if not label_span:
            continue

        label = _norm_label(_text_clean(label_span))
        key = _match_label(label) or _match_label(label.rstrip("иыae"))
        if not key:
            continue

        values = _extract_value_nodes_from_li(li, label_span)
        if values:
            acc[key].extend(values)

    for k in acc:
        acc[k] = _clean_names(acc[k])
    acc["platforms"] = _normalize_platforms(acc["platforms"])
    return acc


def _extract_from_dtdd(root: Tag) -> dict[str, list[str]]:
    acc: dict[str, list[str]] = {"developers": [], "publishers": [], "genres": [], "platforms": []}
    for dt in root.find_all(["dt", "th"]):
        target_key = _match_label(_norm_label(_text_clean(dt)))
        if not target_key:
            continue
        dd = dt.find_next_sibling(["dd", "td"])
        if not dd:
            continue
        links = [a.get_text(" ", strip=True) for a in dd.find_all("a")]
        values = links if links else _split_values(_text_clean(dd))
        if values:
            acc[target_key].extend(values)
    for k in acc:
        acc[k] = _clean_names(acc[k])
    acc["platforms"] = _normalize_platforms(acc["platforms"])
    return acc


def _merge_dicts_of_lists(a: dict[str, list[str]], b: dict[str, list[str]]) -> dict[str, list[str]]:
    out = {k: list(a.get(k, [])) for k in ("developers", "publishers", "genres", "platforms")}
    for k in out:
        out[k] = _clean_names(out[k] + b.get(k, []))
    if out.get("platforms"):
        out["platforms"] = _normalize_platforms(out["platforms"])
    return out


def _html_fallback_extract(root: Tag) -> dict[str, list[str]]:
    acc = {"developers": [], "publishers": [], "genres": [], "platforms": []}
    acc = _merge_dicts_of_lists(acc, _extract_from_ul_blocks(root))
    if not any(acc.values()):
        acc = _merge_dicts_of_lists(acc, _extract_from_dtdd(root))
    if not any(acc.values()):
        table_acc = {"developers": [], "publishers": [], "genres": [], "platforms": []}
        for tr in root.find_all("tr"):
            th, td = tr.find("th"), tr.find("td")
            if not th or not td:
                continue
            key = _match_label(_norm_label(_text_clean(th)))
            if not key:
                continue
            links = [a.get_text(" ", strip=True) for a in td.find_all("a")]
            table_acc[key].extend(links if links else _split_values(_text_clean(td)))
        acc = _merge_dicts_of_lists(acc, table_acc)

    for k in acc:
        acc[k] = _clean_names(acc[k])
    acc["platforms"] = _normalize_platforms(acc["platforms"])
    return acc


def _norm_list(lst: list[str]) -> list[str]:
    s = {x.strip() for x in (lst or []) if x and x.strip() and len(x.strip()) <= 200}
    return sorted(s, key=str.lower)


def parse_html(html: str) -> MGLGameData:
    """Извлекает данные об игре из HTML страницы карточки игры."""

    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")

    main = _pick_main_container(soup)

    h1 = (main.find("h1") if main else None) or soup.find("h1")
    title = h1.get_text(strip=True) if h1 else None

    year = None
    if h1:
        chunks = []
        for i, node in enumerate(h1.next_elements):
            t = node.get_text(" ", strip=True) if hasattr(node, "get_text") else str(node).strip()
            if t:
                chunks.append(t)
            if i >= 12:
                break
        m = _YEAR_RE.search(" ".join(chunks))
        if m:
            year = int(m.group(1))
    if year is None:
        for t in (main or soup).stripped_strings:
            m = _YEAR_RE.search(t)
            if m:
                year = int(m.group(1))
                break

    cover_url = _extract_cover(main or soup)

    jsonld = _parse_jsonld_blocks(soup)
    developers, publishers = list(jsonld["developers"]), list(jsonld["publishers"])
    genres, platforms = list(jsonld["genres"]), list(jsonld["platforms"])

    if not (developers and publishers and genres and platforms):
        html_data = _html_fallback_extract(main or soup)
        developers = developers or html_data["developers"]
        publishers = publishers or html_data["publishers"]
        genres = genres or html_data["genres"]
        platforms = platforms or html_data["platforms"]

    return MGLGameData(
        title=title,
        year=year,
        cover_url=cover_url,
        developers=_norm_list(developers),
        publishers=_norm_list(publishers),
        genres=_norm_list(genres),
        platforms=_norm_list(_normalize_platforms(platforms)),
    )
