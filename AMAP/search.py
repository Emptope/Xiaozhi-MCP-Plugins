from mcp.server.fastmcp import FastMCP
import sys
from loguru import logger
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure loguru logger
logger.remove()
logger.add(sys.stderr, format="{time:YYYY-MM-DD HH:mm:ss} | {level} | Search | {message}", level="INFO")

# Fix UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stderr.reconfigure(encoding='utf-8')
    sys.stdout.reconfigure(encoding='utf-8')

# Create MCP server
mcp = FastMCP("Search")

def _get_api_key():
    """Get API key from environment variables."""
    api_key = os.getenv('AMAP_API_KEY')
    if not api_key:
        logger.error("AMAP_API_KEY not set")
        return None
    return api_key

def _make_search_request(url: str, params: dict):
    """Make search API request."""
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        return None

@mcp.tool()
def search_poi(keywords: str, city: str = None, longitude: float = None, latitude: float = None, radius: int = 3000) -> dict:
    """
    Search for POI (Points of Interest) by keywords.
    
    Args:
        keywords: Search keywords (e.g., "餐厅", "加油站", "银行")
        city: City name to limit search scope (optional)
        longitude: Center longitude for nearby search (optional)
        latitude: Center latitude for nearby search (optional)
        radius: Search radius in meters when using coordinates (default: 3000)
    
    Returns:
        Dictionary containing POI search results
    """
    logger.info(f"Searching POI: {keywords}")
    
    # Check API key
    api_key = _get_api_key()
    if not api_key:
        return {"success": False, "error": "AMAP_API_KEY not configured"}
    
    # Prepare request
    url = "https://restapi.amap.com/v3/place/text"
    params = {
        'key': api_key,
        'keywords': keywords,
        'output': 'json'
    }
    
    # Add city filter if provided
    if city:
        params['city'] = city
        logger.info(f"Using city filter: {city}")
    
    # Add location filter if coordinates provided
    if longitude is not None and latitude is not None:
        if (-180 <= longitude <= 180) and (-90 <= latitude <= 90):
            params['location'] = f"{longitude},{latitude}"
            params['radius'] = min(max(radius, 0), 50000)  # Limit radius to 50km
            logger.info(f"Using location filter: {longitude},{latitude} (radius: {params['radius']}m)")
        else:
            return {"success": False, "error": "Invalid coordinates"}
    
    # Make API request
    data = _make_search_request(url, params)
    if not data:
        return {"success": False, "error": "Failed to fetch search data"}
    
    # Parse response
    if data.get('status') != '1':
        error_msg = data.get('info', 'Unknown API error')
        logger.error(f"API error for {keywords}: {error_msg}")
        return {"success": False, "error": f"API error: {error_msg}"}
    
    # Extract POI data
    pois = data.get('pois', [])
    
    poi_list = []
    for poi in pois:
        location = poi.get('location', '').split(',')
        poi_info = {
            "name": poi.get('name'),
            "type": poi.get('type'),
            "address": poi.get('address'),
            "pname": poi.get('pname'),  # Province name
            "cityname": poi.get('cityname'),
            "adname": poi.get('adname'),  # District name
            "longitude": float(location[0]) if len(location) == 2 else None,
            "latitude": float(location[1]) if len(location) == 2 else None,
            "tel": poi.get('tel'),
            "distance": poi.get('distance'),
            "business_area": poi.get('business_area')
        }
        poi_list.append(poi_info)
    
    result = {
        "success": True,
        "type": "poi_search",
        "keywords": keywords,
        "count": len(poi_list),
        "pois": poi_list
    }
    
    if city:
        result["city"] = city
    if longitude is not None and latitude is not None:
        result["center"] = {"longitude": longitude, "latitude": latitude, "radius": params.get('radius')}
    
    logger.info(f"Found {len(poi_list)} POIs for: {keywords}")
    return result

@mcp.tool()
def search_poi_around(longitude: float, latitude: float, keywords: str = None, radius: int = 1000) -> dict:
    """
    Search POI around specified coordinates.
    
    Args:
        longitude: Center longitude coordinate
        latitude: Center latitude coordinate
        keywords: POI keywords to search (optional)
        radius: Search radius in meters (default: 1000)
    
    Returns:
        Dictionary containing nearby POI information
    """
    logger.info(f"Searching POI around: {longitude}, {latitude}")
    
    # Check API key
    api_key = _get_api_key()
    if not api_key:
        return {"success": False, "error": "AMAP_API_KEY not configured"}
    
    # Validate coordinates
    if not (-180 <= longitude <= 180) or not (-90 <= latitude <= 90):
        return {"success": False, "error": "Invalid coordinates"}
    
    # Validate radius
    if radius < 0 or radius > 50000:
        radius = 1000
        logger.warning("Radius adjusted to 1000m (valid range: 0-50000)")
    
    # Prepare request
    url = "https://restapi.amap.com/v3/place/around"
    params = {
        'key': api_key,
        'location': f"{longitude},{latitude}",
        'radius': radius,
        'output': 'json'
    }
    
    if keywords:
        params['keywords'] = keywords
        logger.info(f"Using keywords filter: {keywords}")
    
    # Make API request
    data = _make_search_request(url, params)
    if not data:
        return {"success": False, "error": "Failed to fetch nearby POI data"}
    
    # Parse response
    if data.get('status') != '1':
        error_msg = data.get('info', 'Unknown API error')
        logger.error(f"API error for {longitude},{latitude}: {error_msg}")
        return {"success": False, "error": f"API error: {error_msg}"}
    
    # Extract POI data
    pois = data.get('pois', [])
    
    poi_list = []
    for poi in pois:
        location = poi.get('location', '').split(',')
        poi_info = {
            "name": poi.get('name'),
            "type": poi.get('type'),
            "address": poi.get('address'),
            "pname": poi.get('pname'),
            "cityname": poi.get('cityname'),
            "adname": poi.get('adname'),
            "longitude": float(location[0]) if len(location) == 2 else None,
            "latitude": float(location[1]) if len(location) == 2 else None,
            "tel": poi.get('tel'),
            "distance": poi.get('distance'),
            "direction": poi.get('direction')
        }
        poi_list.append(poi_info)
    
    result = {
        "success": True,
        "type": "nearby_poi_search",
        "center": {"longitude": longitude, "latitude": latitude},
        "radius": radius,
        "keywords": keywords,
        "count": len(poi_list),
        "pois": poi_list
    }
    
    logger.info(f"Found {len(poi_list)} nearby POIs around {longitude},{latitude}")
    return result

# Start server
if __name__ == "__main__":
    logger.info("Search MCP Server starting...")
    mcp.run(transport="stdio")