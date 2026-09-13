from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


_TRACKING_KEYS = {
    "fbclid",
    "gclid",
    "igsh",
    "igshid",
    "ref",
    "ref_src",
    "si",
    "source",
    "feature",
}


def _clean_query(query: str, *, keep: set[str] | None = None) -> str:
    keep = keep or set()
    filtered = []
    for key, value in parse_qsl(query, keep_blank_values=True):
        lowered = key.casefold()
        if key in keep:
            filtered.append((key, value))
            continue
        if lowered.startswith("utm_") or lowered in _TRACKING_KEYS:
            continue
        filtered.append((key, value))
    return urlencode(filtered, doseq=True)


def _normalized_host(host: str) -> str:
    lowered = host.casefold().split(":", 1)[0]
    if lowered.startswith("www."):
        lowered = lowered[4:]
    return lowered


def canonicalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if not parsed.scheme:
        parsed = urlparse(f"https://{url.strip()}")

    host = _normalized_host(parsed.netloc)
    path = parsed.path or "/"
    query = parsed.query

    if host in {"twitter.com", "mobile.twitter.com", "x.com", "mobile.x.com"}:
        host = "x.com"
        parts = [part for part in path.split("/") if part]
        if len(parts) >= 3 and parts[1] == "status":
            path = f"/{parts[0]}/status/{parts[2]}"
        query = ""
    elif host == "youtu.be":
        video_id = path.strip("/").split("/")[0]
        host = "youtube.com"
        path = "/watch"
        query = urlencode({"v": video_id}) if video_id else ""
    elif host in {"youtube.com", "m.youtube.com"}:
        host = "youtube.com"
        parts = [part for part in path.split("/") if part]
        if parts and parts[0] in {"shorts", "embed"} and len(parts) >= 2:
            path = "/watch"
            query = urlencode({"v": parts[1]})
        elif path == "/watch":
            query = _clean_query(query, keep={"v"})
        else:
            query = _clean_query(query)
    elif host.endswith("tiktok.com"):
        host = "tiktok.com"
        query = ""
    elif host.endswith("instagram.com"):
        host = "instagram.com"
        query = ""
    elif host.endswith("reddit.com"):
        host = "reddit.com"
        query = ""
    else:
        query = _clean_query(query)

    normalized_path = "/" + "/".join(part for part in path.split("/") if part)
    if normalized_path == "/":
        normalized_path = "/"
    return urlunparse(("https", host, normalized_path, "", query, ""))


def infer_platform_from_url(url: str) -> str:
    host = _normalized_host(urlparse(canonicalize_url(url)).netloc)
    if host == "x.com":
        return "x"
    if host == "tiktok.com" or host.endswith(".tiktok.com"):
        return "tiktok"
    if host == "instagram.com" or host.endswith(".instagram.com"):
        return "instagram"
    if host == "reddit.com" or host.endswith(".reddit.com"):
        return "reddit"
    if host == "youtube.com" or host.endswith(".youtube.com"):
        return "youtube"
    return "web"
