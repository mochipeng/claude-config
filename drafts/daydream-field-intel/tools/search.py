from ddgs import DDGS


def web_search(query: str, max_results: int = 6) -> str:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return "No results found."
        lines = []
        for r in results:
            lines.append(f"Title: {r.get('title', '')}")
            lines.append(f"URL: {r.get('href', '')}")
            lines.append(f"Snippet: {r.get('body', '')}")
            lines.append("---")
        return "\n".join(lines)
    except Exception as e:
        return f"Search error: {e}"
