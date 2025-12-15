from langchain_core.tools import tool
import httpx
import os
from typing import Optional

@tool
def web_search(query: str) -> str:
    """
    Fallback web search when iFixit returns no results.
    Uses Tavily API if available, otherwise DuckDuckGo.
    Triggered when iFixit returns 'Status: Not Found' or zero results.
    """
    # Try Tavily first (requires API key)
    tavily_key = os.getenv("TAVILY_API_KEY")
    if tavily_key:
        result = _search_tavily(query, tavily_key)
        if result:
            return result
    
    # Fallback to DuckDuckGo instant answer API
    return _search_duckduckgo(query)


def _search_tavily(query: str, api_key: str) -> Optional[str]:
    """
    Search using Tavily API.
    Returns cleaned search results.
    """
    try:
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": api_key,
            "query": query,
            "search_depth": "basic",
            "max_results": 3
        }
        
        response = httpx.post(url, json=payload, timeout=10.0)
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        results = data.get("results", [])
        
        if not results:
            return None
        
        cleaned = "Web search results:\n\n"
        for idx, result in enumerate(results[:3], 1):
            title = result.get("title", "No title")
            content = result.get("content", "No content")
            url = result.get("url", "")
            
            cleaned += f"**{idx}. {title}**\n"
            cleaned += f"{content[:200]}...\n"
            cleaned += f"Source: {url}\n\n"
        
        return cleaned
        
    except Exception as e:
        return None


def _search_duckduckgo(query: str) -> str:
    """
    Search using DuckDuckGo Instant Answer API.
    Returns cleaned search results.
    """
    try:
        url = "https://api.duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
            "no_html": 1,
            "skip_disambig": 1
        }
        
        response = httpx.get(url, params=params, timeout=10.0)
        
        if response.status_code != 200:
            return f"Unable to perform web search at this time. Try searching for '{query}' manually."
        
        data = response.json()
        
        # Get abstract/summary
        abstract = data.get("Abstract", "")
        abstract_source = data.get("AbstractSource", "")
        abstract_url = data.get("AbstractURL", "")
        
        if abstract:
            result = f"**Web Search Result:**\n\n{abstract}\n\n"
            if abstract_source:
                result += f"Source: {abstract_source}"
            if abstract_url:
                result += f" ({abstract_url})"
            return result
        
        # Try related topics if no abstract
        related = data.get("RelatedTopics", [])
        if related:
            result = "**Related Information:**\n\n"
            for idx, topic in enumerate(related[:3], 1):
                if isinstance(topic, dict):
                    text = topic.get("Text", "")
                    url = topic.get("FirstURL", "")
                    if text:
                        result += f"{idx}. {text}\n"
                        if url:
                            result += f"   {url}\n"
            return result
        
        return f"No detailed web results found. Try searching for '{query}' on Google or YouTube for repair videos."
        
    except Exception as e:
        return f"Web search error: {str(e)}. Try searching for '{query}' manually on Google or YouTube."
