"""Open websites and search them, with short names like "youtube"."""

import webbrowser
from urllib.parse import quote


SEARCH_ENGINES = {
    "google": "https://www.google.com/search?q=",
    "youtube": "https://www.youtube.com/results?search_query=",
    "github": "https://github.com/search?q=",
    "wikipedia": "https://en.wikipedia.org/wiki/",
    "amazon": "https://www.amazon.in/s?k=",
    "flipkart": "https://www.flipkart.com/search?q=",
    "spotify": "https://open.spotify.com/search/",
}

SITE_ALIASES = {
    "youtube": "https://www.youtube.com",
    "yt": "https://www.youtube.com",
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "google drive": "https://drive.google.com",
    "drive": "https://drive.google.com",
    "google docs": "https://docs.google.com",
    "docs": "https://docs.google.com",
    "sheets": "https://sheets.google.com",
    "google maps": "https://maps.google.com",
    "maps": "https://maps.google.com",
    "google meet": "https://meet.google.com",
    "meet": "https://meet.google.com",
    "github": "https://github.com",
    "gitlab": "https://gitlab.com",
    "stackoverflow": "https://stackoverflow.com",
    "stack overflow": "https://stackoverflow.com",
    "chatgpt": "https://chatgpt.com",
    "chat gpt": "https://chatgpt.com",
    "gemini": "https://gemini.google.com",
    "claude": "https://claude.ai",
    "whatsapp": "https://web.whatsapp.com",
    "whatsapp web": "https://web.whatsapp.com",
    "telegram": "https://web.telegram.org",
    "telegram web": "https://web.telegram.org",
    "instagram": "https://www.instagram.com",
    "insta": "https://www.instagram.com",
    "facebook": "https://www.facebook.com",
    "fb": "https://www.facebook.com",
    "twitter": "https://x.com",
    "x": "https://x.com",
    "linkedin": "https://www.linkedin.com",
    "reddit": "https://www.reddit.com",
    "netflix": "https://www.netflix.com",
    "prime video": "https://www.primevideo.com",
    "hotstar": "https://www.hotstar.com",
    "spotify": "https://open.spotify.com",
    "amazon": "https://www.amazon.in",
    "flipkart": "https://www.flipkart.com",
    "myntra": "https://www.myntra.com",
    "wikipedia": "https://en.wikipedia.org",
}


def site_url(name: str):
    """Return a URL for a spoken site name, or None when it is unknown."""

    key = " ".join((name or "").strip().lower().split())

    if not key:
        return None

    if key in SITE_ALIASES:
        return SITE_ALIASES[key]

    if key.startswith(("http://", "https://", "www.")):
        return key

    if "." in key and " " not in key:
        return key

    return None


def google_search(query: str):

    query = query.strip()

    url = SEARCH_ENGINES["google"] + quote(query)

    webbrowser.open(url)

    return {
        "success": True,
        "action": "google_search",
        "query": query,
        "url": url,
        "message": f"Searching Google for '{query}'"
    }


def youtube_search(query: str):

    query = query.strip()

    url = SEARCH_ENGINES["youtube"] + quote(query)

    webbrowser.open(url)

    return {
        "success": True,
        "action": "youtube_search",
        "query": query,
        "url": url,
        "message": f"Searching YouTube for '{query}'"
    }


def github_search(query: str):

    query = query.strip()

    url = SEARCH_ENGINES["github"] + quote(query)

    webbrowser.open(url)

    return {
        "success": True,
        "action": "github_search",
        "query": query,
        "url": url,
        "message": f"Searching GitHub for '{query}'"
    }


def search_site(query: str, site: str = "google"):

    query = (query or "").strip()

    key = (site or "google").strip().lower()

    if not query:

        return {"success": False, "error": "Tell me what to search for."}

    base = SEARCH_ENGINES.get(key)

    if base:

        url = base + quote(query)

        webbrowser.open(url)

        return {
            "success": True,
            "action": "search_site",
            "site": key,
            "query": query,
            "url": url,
            "message": f"Searching {key.capitalize()} for '{query}'",
        }

    url_for_site = site_url(key)

    if url_for_site:

        domain = (
            url_for_site.replace("https://", "")
            .replace("http://", "")
            .strip("/")
        )

        url = SEARCH_ENGINES["google"] + quote(f"{query} site:{domain}")

        webbrowser.open(url)

        return {
            "success": True,
            "action": "search_site",
            "site": key,
            "query": query,
            "url": url,
            "message": f"Searching {key} for '{query}'",
        }

    return {"success": False, "error": f"I don't know how to search on '{site}'."}


def open_website(url: str):

    url = url.strip()

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    webbrowser.open(url)

    return {
        "success": True,
        "action": "open_website",
        "url": url,
        "message": f"Opening {url}"
    }


def open_site(name: str):

    url = site_url(name)

    if url is None:

        return {
            "success": False,
            "site": name,
            "error": f"I don't know the site '{name}'.",
        }

    result = open_website(url)

    result["site"] = name
    result["message"] = f"Opening {name} ({result['url']})."

    return result
