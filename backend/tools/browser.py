import webbrowser
from urllib.parse import quote


SEARCH_ENGINES = {
    "google": "https://www.google.com/search?q=",
    "youtube": "https://www.youtube.com/results?search_query=",
    "github": "https://github.com/search?q=",
    "wikipedia": "https://en.wikipedia.org/wiki/",
}


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