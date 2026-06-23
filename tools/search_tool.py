from ddgs import DDGS


def web_search(query: str, max_results: int = 3) -> str:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))

        if not results:
            return "No results found."

        formatted = ""
        for i, r in enumerate(results, 1):
            formatted += f"{i}. {r['title']}\n{r['body']}\n\n"

        return formatted.strip()

    except Exception as e:
        return f"Search failed: {str(e)}"