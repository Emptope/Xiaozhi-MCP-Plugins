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
logger.add(sys.stderr, format="{time:YYYY-MM-DD HH:mm:ss} | {level} | Location | {message}", level="INFO")

# Fix UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stderr.reconfigure(encoding='utf-8')
    sys.stdout.reconfigure(encoding='utf-8')

# Create MCP server
mcp = FastMCP("Location")

def _get_api_key():
    """Get API key from environment variables."""
    api_key = os.getenv('AMAP_API_KEY')
    if not api_key:
        logger.error("AMAP_API_KEY not set")
        return None
    return api_key

def _make_geocode_request(url: str, params: dict):
    """Make geocoding API request."""
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        return None

@mcp.tool()
def geocode_address(address: str, city: str = None) -> dict:
    """
    Convert address to coordinates (geocoding).
    
    Args:
        address: Address to geocode (e.g., "天安门", "北京市朝阳区阜通东大街6号")
        city: City name for more accurate results (optional)
    
    Returns:
        Dictionary containing coordinate information
    """
    logger.info(f"Geocoding address: {address}")
    
    # Check API key
    api_key = _get_api_key()
    if not api_key:
        return {"success": False, "error": "AMAP_API_KEY not configured"}
    
    # Prepare request
    url = "https://restapi.amap.com/v3/geocode/geo"
    params = {
        'key': api_key,
        'address': address,
        'output': 'json'
    }
    
    if city:
        params['city'] = city
        logger.info(f"Using city filter: {city}")
    
    # Make API request
    data = _make_geocode_request(url, params)
    if not data:
        return {"success": False, "error": "Failed to fetch geocoding data"}
    
    # Parse response
    if data.get('status') != '1':
        error_msg = data.get('info', 'Unknown API error')
        logger.error(f"API error for {address}: {error_msg}")
        return {"success": False, "error": f"API error: {error_msg}"}
    
    # Extract geocoding data
    geocodes = data.get('geocodes', [])
    if not geocodes:
        logger.warning(f"No geocoding data for: {address}")
        return {"success": False, "error": "Address not found"}
    
    geocode = geocodes[0]
    location = geocode.get('location', '').split(',')
    
    if len(location) != 2:
        logger.error(f"Invalid location format: {geocode.get('location')}")
        return {"success": False, "error": "Invalid location data"}
    
    result = {
        "success": True,
        "type": "geocoding",
        "address": geocode.get('formatted_address'),
        "province": geocode.get('province'),
        "city": geocode.get('city'),
        "district": geocode.get('district'),
        "adcode": geocode.get('adcode'),
        "longitude": float(location[0]),
        "latitude": float(location[1]),
        "location": geocode.get('location'),
        "level": geocode.get('level')
    }
    
    logger.info(f"Geocoded {address}: {location[0]}, {location[1]}")
    return result

@mcp.tool()
def reverse_geocode(longitude: float, latitude: float, radius: int = 1000) -> dict:
    """
    Convert coordinates to address (reverse geocoding).
    
    Args:
        longitude: Longitude coordinate
        latitude: Latitude coordinate
        radius: Search radius in meters (default: 1000)
    
    Returns:
        Dictionary containing address information
    """
    logger.info(f"Reverse geocoding: {longitude}, {latitude}")
    
    # Check API key
    api_key = _get_api_key()
    if not api_key:
        return {"success": False, "error": "AMAP_API_KEY not configured"}
    
    # Validate coordinates
    if not (-180 <= longitude <= 180) or not (-90 <= latitude <= 90):
        return {"success": False, "error": "Invalid coordinates"}
    
    # Validate radius
    if radius < 0 or radius > 3000:
        radius = 1000
        logger.warning("Radius adjusted to 1000m (valid range: 0-3000)")
    
    # Prepare request
    url = "https://restapi.amap.com/v3/geocode/regeo"
    params = {
        'key': api_key,
        'location': f"{longitude},{latitude}",
        'radius': radius,
        'extensions': 'base',
        'output': 'json'
    }
    
    # Make API request
    data = _make_geocode_request(url, params)
    if not data:
        return {"success": False, "error": "Failed to fetch reverse geocoding data"}
    
    # Parse response
    if data.get('status') != '1':
        error_msg = data.get('info', 'Unknown API error')
        logger.error(f"API error for {longitude},{latitude}: {error_msg}")
        return {"success": False, "error": f"API error: {error_msg}"}
    
    # Extract reverse geocoding data
    regeocode = data.get('regeocode', {})
    if not regeocode:
        logger.warning(f"No reverse geocoding data for: {longitude},{latitude}")
        return {"success": False, "error": "Location not found"}
    
    address_component = regeocode.get('addressComponent', {})
    
    result = {
        "success": True,
        "type": "reverse_geocoding",
        "formatted_address": regeocode.get('formatted_address'),
        "country": address_component.get('country'),
        "province": address_component.get('province'),
        "city": address_component.get('city'),
        "district": address_component.get('district'),
        "township": address_component.get('township'),
        "adcode": address_component.get('adcode'),
        "longitude": longitude,
        "latitude": latitude,
        "radius": radius
    }
    
    # Add street information if available
    street_number = address_component.get('streetNumber', {})
    if street_number:
        result.update({
            "street": street_number.get('street'),
            "number": street_number.get('number'),
            "direction": street_number.get('direction'),
            "distance": street_number.get('distance')
        })
    
    logger.info(f"Reverse geocoded {longitude},{latitude}: {regeocode.get('formatted_address')}")
    return result

# Start server
if __name__ == "__main__":
    logger.info("Location MCP Server starting...")
    mcp.run(transport="stdio")