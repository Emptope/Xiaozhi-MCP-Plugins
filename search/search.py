from mcp.server.fastmcp import FastMCP
import sys
from loguru import logger
import requests
import os
from dotenv import load_dotenv
import json
from urllib.parse import quote, urljoin
import time
from typing import List, Dict, Any

# Load environment variables
load_dotenv()

# Configure loguru logger to output to stderr
logger.remove()  # Remove default handler
logger.add(sys.stderr, format="{time:YYYY-MM-DD HH:mm:ss} | {level} | Search | {message}", level="INFO")

# Fix UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stderr.reconfigure(encoding='utf-8')
    sys.stdout.reconfigure(encoding='utf-8')

# Default search engine configuration
def get_default_search_engine() -> str:
    """Get the default search engine from environment variable or return 'google'"""
    default_engine = os.getenv('DEFAULT_SEARCH_ENGINE', 'google').lower()
    supported_engines = ['duckduckgo', 'bing', 'google', 'baidu']
    
    if default_engine not in supported_engines:
        logger.warning(f"Unsupported default search engine '{default_engine}', falling back to 'google'")
        return 'google'
    
    logger.info(f"Default search engine set to: {default_engine}")
    return default_engine

# Get the default search engine
DEFAULT_SEARCH_ENGINE = get_default_search_engine()

# Create an MCP server
mcp = FastMCP("Search")

@mcp.tool()
def web_search(query: str, engine: str = None, max_results: int = 10, language: str = "zh-cn") -> dict:
    """
    Perform web search using various search engines
    
    Args:
        query: Search query string
        engine: Search engine to use (duckduckgo, bing, google, baidu). If not specified, uses default engine (google)
        max_results: Maximum number of results to return (1-20), default is 10
        language: Language preference (zh-cn, en-us, etc.), default is zh-cn
    
    Returns:
        Dictionary containing search results
    """
    # Use default engine if not specified
    if engine is None:
        engine = DEFAULT_SEARCH_ENGINE
        logger.info(f"Using default search engine: {engine}")
    
    logger.info(f"Web search started: '{query}' using {engine}")
    
    # Validate parameters
    max_results = min(max(max_results, 1), 20)  # Limit between 1-20
    
    try:
        if engine.lower() == "duckduckgo":
            return _search_duckduckgo(query, max_results, language)
        elif engine.lower() == "bing":
            return _search_bing(query, max_results, language)
        elif engine.lower() == "google":
            return _search_google(query, max_results, language)
        elif engine.lower() == "baidu":
            return _search_baidu(query, max_results, language)
        else:
            logger.error(f"Unsupported search engine: {engine}")
            return {"success": False, "error": f"Unsupported search engine: {engine}. Supported engines: duckduckgo, bing, google, baidu"}
    
    except Exception as e:
        error_msg = f"Search error: {str(e)}"
        logger.error(f"Error searching '{query}' with {engine}: {error_msg}")
        return {"success": False, "error": error_msg}

@mcp.tool()
def get_search_config() -> dict:
    """
    Get current search configuration
    
    Returns:
        Dictionary containing current search configuration
    """
    try:
        config = {
            "default_search_engine": DEFAULT_SEARCH_ENGINE,
            "supported_engines": ["duckduckgo", "bing", "google", "baidu"],
            "api_keys_configured": {
                "bing": bool(os.getenv('BING_SEARCH_API_KEY')),
                "google": bool(os.getenv('GOOGLE_SEARCH_API_KEY') and os.getenv('GOOGLE_SEARCH_ENGINE_ID')),
                "news": bool(os.getenv('NEWS_API_KEY'))
            },
            "fallback_engine": "duckduckgo"
        }
        
        logger.info("Search configuration retrieved")
        return {"success": True, "config": config}
        
    except Exception as e:
        error_msg = f"Error getting search config: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}

def _search_duckduckgo(query: str, max_results: int, language: str) -> dict:
    """Search using DuckDuckGo Instant Answer API"""
    try:
        # DuckDuckGo Instant Answer API
        url = "https://api.duckduckgo.com/"
        params = {
            'q': query,
            'format': 'json',
            'no_html': '1',
            'skip_disambig': '1'
        }
        
        logger.info(f"Sending DuckDuckGo API request for: {query}")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        results = []
        
        # Add abstract if available
        if data.get('Abstract'):
            results.append({
                "title": data.get('Heading', query),
                "snippet": data.get('Abstract'),
                "url": data.get('AbstractURL', ''),
                "source": data.get('AbstractSource', 'DuckDuckGo')
            })
        
        # Add related topics
        for topic in data.get('RelatedTopics', [])[:max_results-len(results)]:
            if isinstance(topic, dict) and topic.get('Text'):
                results.append({
                    "title": topic.get('Text', '').split(' - ')[0] if ' - ' in topic.get('Text', '') else topic.get('Text', ''),
                    "snippet": topic.get('Text', ''),
                    "url": topic.get('FirstURL', ''),
                    "source": "DuckDuckGo"
                })
        
        # Add definition if available
        if data.get('Definition') and len(results) < max_results:
            results.append({
                "title": f"Definition: {query}",
                "snippet": data.get('Definition'),
                "url": data.get('DefinitionURL', ''),
                "source": data.get('DefinitionSource', 'DuckDuckGo')
            })
        
        logger.info(f"DuckDuckGo search completed: {len(results)} results for '{query}'")
        
        return {
            "success": True,
            "engine": "DuckDuckGo",
            "query": query,
            "total_results": len(results),
            "results": results[:max_results]
        }
        
    except Exception as e:
        logger.error(f"DuckDuckGo search error: {str(e)}")
        return {"success": False, "error": f"DuckDuckGo search failed: {str(e)}"}

def _search_bing(query: str, max_results: int, language: str) -> dict:
    """Search using Bing Search API (requires API key)"""
    try:
        api_key = os.getenv('BING_SEARCH_API_KEY')
        if not api_key:
            logger.warning("BING_SEARCH_API_KEY not set, falling back to DuckDuckGo")
            return _search_duckduckgo(query, max_results, language)
        
        url = "https://api.bing.microsoft.com/v7.0/search"
        headers = {
            'Ocp-Apim-Subscription-Key': api_key
        }
        params = {
            'q': query,
            'count': max_results,
            'mkt': language,
            'textDecorations': False,
            'textFormat': 'Raw'
        }
        
        logger.info(f"Sending Bing API request for: {query}")
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        results = []
        for item in data.get('webPages', {}).get('value', []):
            results.append({
                "title": item.get('name', ''),
                "snippet": item.get('snippet', ''),
                "url": item.get('url', ''),
                "source": "Bing"
            })
        
        logger.info(f"Bing search completed: {len(results)} results for '{query}'")
        
        return {
            "success": True,
            "engine": "Bing",
            "query": query,
            "total_results": len(results),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Bing search error: {str(e)}")
        return {"success": False, "error": f"Bing search failed: {str(e)}"}

def _search_google(query: str, max_results: int, language: str) -> dict:
    """Search using Google Custom Search API (requires API key and search engine ID)"""
    try:
        api_key = os.getenv('GOOGLE_SEARCH_API_KEY')
        search_engine_id = os.getenv('GOOGLE_SEARCH_ENGINE_ID')
        
        if not api_key or not search_engine_id:
            logger.warning("Google API credentials not set, falling back to DuckDuckGo")
            return _search_duckduckgo(query, max_results, language)
        
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': api_key,
            'cx': search_engine_id,
            'q': query,
            'num': min(max_results, 10),  # Google API max is 10
            'lr': f'lang_{language.split("-")[0]}' if language else 'lang_zh'
        }
        
        logger.info(f"Sending Google API request for: {query}")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        results = []
        for item in data.get('items', []):
            results.append({
                "title": item.get('title', ''),
                "snippet": item.get('snippet', ''),
                "url": item.get('link', ''),
                "source": "Google"
            })
        
        logger.info(f"Google search completed: {len(results)} results for '{query}'")
        
        return {
            "success": True,
            "engine": "Google",
            "query": query,
            "total_results": len(results),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Google search error: {str(e)}")
        return {"success": False, "error": f"Google search failed: {str(e)}"}

def _search_baidu(query: str, max_results: int, language: str) -> dict:
    """Search using a simple web scraping approach for Baidu (for demonstration)"""
    try:
        # Note: This is a simplified implementation for demonstration
        # In production, you should use official APIs when available
        logger.warning("Baidu search using simplified method, falling back to DuckDuckGo")
        return _search_duckduckgo(query, max_results, language)
        
    except Exception as e:
        logger.error(f"Baidu search error: {str(e)}")
        return {"success": False, "error": f"Baidu search failed: {str(e)}"}

@mcp.tool()
def search_news(query: str, max_results: int = 10, language: str = "zh-cn") -> dict:
    """
    Search for news articles related to the query
    
    Args:
        query: Search query for news
        max_results: Maximum number of news results to return (1-20), default is 10
        language: Language preference (zh-cn, en-us, etc.), default is zh-cn
    
    Returns:
        Dictionary containing news search results
    """
    logger.info(f"News search started: '{query}'")
    
    try:
        # Use NewsAPI if available, otherwise fall back to general search
        api_key = os.getenv('NEWS_API_KEY')
        
        if api_key:
            return _search_news_api(query, max_results, language, api_key)
        else:
            logger.warning("NEWS_API_KEY not set, using general web search for news")
            # Add "news" to the query for better news results
            news_query = f"{query} news 新闻"
            return web_search(news_query, DEFAULT_SEARCH_ENGINE, max_results, language)
    
    except Exception as e:
        error_msg = f"News search error: {str(e)}"
        logger.error(f"Error searching news for '{query}': {error_msg}")
        return {"success": False, "error": error_msg}

def _search_news_api(query: str, max_results: int, language: str, api_key: str) -> dict:
    """Search news using NewsAPI"""
    try:
        url = "https://newsapi.org/v2/everything"
        params = {
            'q': query,
            'apiKey': api_key,
            'pageSize': min(max_results, 100),
            'sortBy': 'publishedAt',
            'language': language.split('-')[0] if language else 'zh'
        }
        
        logger.info(f"Sending NewsAPI request for: {query}")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('status') != 'ok':
            raise Exception(f"NewsAPI error: {data.get('message', 'Unknown error')}")
        
        results = []
        for article in data.get('articles', []):
            results.append({
                "title": article.get('title', ''),
                "snippet": article.get('description', ''),
                "url": article.get('url', ''),
                "source": article.get('source', {}).get('name', 'NewsAPI'),
                "published_at": article.get('publishedAt', ''),
                "author": article.get('author', '')
            })
        
        logger.info(f"NewsAPI search completed: {len(results)} results for '{query}'")
        
        return {
            "success": True,
            "engine": "NewsAPI",
            "query": query,
            "total_results": data.get('totalResults', len(results)),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"NewsAPI search error: {str(e)}")
        return {"success": False, "error": f"NewsAPI search failed: {str(e)}"}

@mcp.tool()
def get_page_content(url: str, max_length: int = 2000) -> dict:
    """
    Get the text content of a web page
    
    Args:
        url: URL of the web page to fetch
        max_length: Maximum length of content to return, default is 2000 characters
    
    Returns:
        Dictionary containing page content
    """
    logger.info(f"Fetching page content: {url}")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Simple text extraction (in production, consider using BeautifulSoup)
        content = response.text
        
        # Basic HTML tag removal
        import re
        content = re.sub(r'<script.*?</script>', '', content, flags=re.DOTALL)
        content = re.sub(r'<style.*?</style>', '', content, flags=re.DOTALL)
        content = re.sub(r'<[^>]+>', '', content)
        content = re.sub(r'\s+', ' ', content).strip()
        
        # Limit content length
        if len(content) > max_length:
            content = content[:max_length] + "..."
        
        logger.info(f"Page content fetched successfully: {len(content)} characters")
        
        return {
            "success": True,
            "url": url,
            "content": content,
            "length": len(content)
        }
        
    except Exception as e:
        error_msg = f"Error fetching page content: {str(e)}"
        logger.error(f"Error fetching {url}: {error_msg}")
        return {"success": False, "error": error_msg}

# Start the server
if __name__ == "__main__":
    logger.info("Search MCP Server starting...")
    logger.info(f"Default search engine: {DEFAULT_SEARCH_ENGINE}")
    mcp.run(transport="stdio")