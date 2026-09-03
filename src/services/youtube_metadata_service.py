import re
from functools import lru_cache
from typing import Optional
from urllib.parse import unquote, urlparse


def normalize_tag(value: str) -> str:
    return " ".join(value.strip().lower().split())


def normalize_topic_category(value: str) -> str:
    raw = value.strip()
    if not raw:
        return ""

    parsed = urlparse(raw)
    if parsed.scheme and parsed.netloc:
        candidate = parsed.path.rstrip("/").split("/")[-1]
        candidate = unquote(candidate).replace("_", " ")
    else:
        candidate = raw.replace("_", " ")

    return re.sub(r"\s+", " ", candidate).strip()


@lru_cache(maxsize=256)
def resolve_category_name(category_id: str, region_code: Optional[str] = None) -> Optional[str]:
    """Resolve a small stable core without making the normal ingest path depend on a network call.

    Unknown categories intentionally return None. A collector that already has a category
    display name should persist it directly; a future YouTube API adapter can extend this
    resolver without changing callers.
    """
    known = {
        "1": "Film & Animation",
        "2": "Autos & Vehicles",
        "10": "Music",
        "15": "Pets & Animals",
        "17": "Sports",
        "19": "Travel & Events",
        "20": "Gaming",
        "22": "People & Blogs",
        "23": "Comedy",
        "24": "Entertainment",
        "25": "News & Politics",
        "26": "Howto & Style",
        "27": "Education",
        "28": "Science & Technology",
        "29": "Nonprofits & Activism",
    }
    return known.get(str(category_id))
