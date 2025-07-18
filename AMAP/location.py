from mcp.server.fastmcp import FastMCP
import sys
from loguru import logger
import requests
import os
import re
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

@mcp.tool()
def ip_location(ip: str = None) -> dict:
    """
    Get location information based on IP address (Basic IP Location).
    
    Args:
        ip: IP address to locate (optional, uses client IP if not provided)
    
    Returns:
        Dictionary containing IP location information
    """
    logger.info(f"IP location lookup: {ip or 'client IP'}")
    
    # Check API key
    api_key = _get_api_key()
    if not api_key:
        return {"success": False, "error": "AMAP_API_KEY not configured"}
    
    # Validate IP address format if provided
    if ip:
        ip_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
        if not re.match(ip_pattern, ip):
            return {"success": False, "error": "Invalid IP address format"}
    
    # Prepare request
    url = "https://restapi.amap.com/v3/ip"
    params = {
        'key': api_key,
        'output': 'json'
    }
    
    if ip:
        params['ip'] = ip
    
    # Make API request
    data = _make_geocode_request(url, params)
    if not data:
        return {"success": False, "error": "Failed to fetch IP location data"}
    
    # Parse response
    if data.get('status') != '1':
        error_msg = data.get('info', 'Unknown API error')
        logger.error(f"API error for IP {ip}: {error_msg}")
        return {"success": False, "error": f"API error: {error_msg}"}
    
    # Extract IP location data
    result = {
        "success": True,
        "type": "ip_location",
        "ip": ip or "client_ip",
        "country": data.get('country'),
        "province": data.get('province'),
        "city": data.get('city'),
        "district": data.get('district'),
        "isp": data.get('isp'),
        "adcode": data.get('adcode')
    }
    
    # Add coordinates if available
    location = data.get('rectangle')
    if location:
        coords = location.split(';')
        if len(coords) >= 2:
            # Rectangle format: "lng1,lat1;lng2,lat2"
            coord1 = coords[0].split(',')
            coord2 = coords[1].split(',')
            if len(coord1) == 2 and len(coord2) == 2:
                # Calculate center point
                center_lng = (float(coord1[0]) + float(coord2[0])) / 2
                center_lat = (float(coord1[1]) + float(coord2[1])) / 2
                result.update({
                    "longitude": center_lng,
                    "latitude": center_lat,
                    "rectangle": location
                })
    
    logger.info(f"IP location for {ip or 'client IP'}: {data.get('province')}, {data.get('city')}")
    return result

@mcp.tool()
def advanced_ip_location(ip: str, location_type: int = 4) -> dict:
    """
    Get detailed location information based on IP address (Advanced IP Location).
    
    Args:
        ip: IP address to locate (required)
        location_type: Location precision type (1-4, default: 4)
                      1: Country level
                      2: Province level  
                      3: City level
                      4: District level (most precise)
    
    Returns:
        Dictionary containing detailed IP location information
    """
    logger.info(f"Advanced IP location lookup: {ip}, type: {location_type}")
    
    # Check API key
    api_key = _get_api_key()
    if not api_key:
        return {"success": False, "error": "AMAP_API_KEY not configured"}
    
    # Validate IP address format
    ip_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    if not re.match(ip_pattern, ip):
        return {"success": False, "error": "Invalid IP address format"}
    
    # Validate location type
    if location_type not in [1, 2, 3, 4]:
        location_type = 4
        logger.warning("Location type adjusted to 4 (valid range: 1-4)")
    
    # Prepare request
    url = "https://restapi.amap.com/v5/ip/location"
    params = {
        'key': api_key,
        'ip': ip,
        'type': location_type
    }
    
    # Make API request
    data = _make_geocode_request(url, params)
    if not data:
        return {"success": False, "error": "Failed to fetch advanced IP location data"}
    
    # Parse response
    if data.get('status') != '1':
        error_msg = data.get('info', 'Unknown API error')
        logger.error(f"Advanced API error for IP {ip}: {error_msg}")
        return {"success": False, "error": f"API error: {error_msg}"}
    
    # Extract advanced IP location data
    result = {
        "success": True,
        "type": "advanced_ip_location",
        "ip": ip,
        "location_type": location_type,
        "country": data.get('country'),
        "province": data.get('province'),
        "city": data.get('city'),
        "district": data.get('district'),
        "isp": data.get('isp'),
        "adcode": data.get('adcode')
    }
    
    # Add precise coordinates if available
    if 'location' in data:
        location_coords = data['location'].split(',')
        if len(location_coords) == 2:
            result.update({
                "longitude": float(location_coords[0]),
                "latitude": float(location_coords[1]),
                "location": data['location']
            })
    
    # Add accuracy radius if available
    if 'radius' in data:
        result['accuracy_radius'] = data['radius']
    
    logger.info(f"Advanced IP location for {ip}: {data.get('province')}, {data.get('city')}")
    return result

# Start server
if __name__ == "__main__":
    logger.info("Location MCP Server starting...")
    mcp.run(transport="stdio")