"""Open websites and search them, with short names like "youtube"."""

import os
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


# Apps that accept a search straight from a URI, so the search happens in
# the installed app instead of the website.
APP_SEARCH_URIS = {
    "spotify": "spotify:search:{query}",
}


def _installed_app(name: str):
    """Path of an installed desktop app for a site name, or None."""

    try:

        from tools.apps import launcher

        return launcher.find_application(" ".join(name.split()))

    except Exception:

        return None


# Only these are searched in their own app; a browser shortcut must never
# swallow a Google or YouTube search.
APP_SEARCH_SITES = {"spotify", "discord", "telegram", "whatsapp", "netflix"}


def _search_in_app(key: str, query: str):
    """Search inside the installed app when there is one."""

    if key not in APP_SEARCH_SITES:

        return None

    if not _installed_app(key):

        return None

    uri = APP_SEARCH_URIS.get(key)

    if uri:

        target = uri.format(query=quote(query))

        try:

            os.startfile(target)

        except Exception:

            webbrowser.open(target)

        return {
            "success": True,
            "action": "search_site",
            "site": key,
            "query": query,
            "app": True,
            "message": f"Searching {key.capitalize()} app for '{query}'",
        }

    # No direct search URI: open the app and keep the query ready to paste.
    try:

        from tools import clipboard
        from tools.apps import launcher

        opened, _message = launcher.open(key)

        if opened:

            clipboard.set_clipboard(query)

            return {
                "success": True,
                "action": "search_site",
                "site": key,
                "query": query,
                "app": True,
                "message": (
                    f"Opened the {key.capitalize()} app; '{query}' is on your "
                    "clipboard, press Ctrl+V in its search box."
                ),
            }

    except Exception:

        pass

    return None


def search_site(query: str, site: str = "google"):

    query = (query or "").strip()

    key = (site or "google").strip().lower()

    if not query:

        return {"success": False, "error": "Tell me what to search for."}

    in_app = _search_in_app(key, query)

    if in_app:

        return in_app

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
