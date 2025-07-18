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
logger.add(sys.stderr, format="{time:YYYY-MM-DD HH:mm:ss} | {level} | Weather | {message}", level="INFO")

# Fix UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stderr.reconfigure(encoding='utf-8')
    sys.stdout.reconfigure(encoding='utf-8')

# Create MCP server
mcp = FastMCP("Weather")

def _get_api_key():
    """Get API key from environment variables."""
    api_key = os.getenv('AMAP_API_KEY')
    if not api_key:
        logger.error("AMAP_API_KEY not set")
        return None
    return api_key

def _make_weather_request(city: str, extensions: str = "base"):
    """Make weather API request."""
    api_key = _get_api_key()
    if not api_key:
        return None
    
    url = "https://restapi.amap.com/v3/weather/weatherInfo"
    params = {
        'key': api_key,
        'city': city,
        'extensions': extensions
    }
    
    try:
        logger.info(f"Requesting weather for {city} (type: {extensions})")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed for {city}: {e}")
        return None

@mcp.tool()
def get_current_weather(city: str) -> dict:
    """
    Get current weather for specified city.
    
    Args:
        city: City name or adcode (e.g., Beijing, 110000)
    
    Returns:
        Dictionary containing current weather information
    """
    logger.info(f"Getting current weather for: {city}")
    
    # Check API key
    if not _get_api_key():
        return {"success": False, "error": "AMAP_API_KEY not configured"}
    
    # Make API request
    data = _make_weather_request(city, "base")
    if not data:
        return {"success": False, "error": "Failed to fetch weather data"}
    
    # Parse response
    if data.get('status') != '1':
        error_msg = data.get('info', 'Unknown API error')
        logger.error(f"API error for {city}: {error_msg}")
        return {"success": False, "error": f"API error: {error_msg}"}
    
    # Extract current weather data
    lives = data.get('lives', [])
    if not lives:
        logger.warning(f"No current weather data for: {city}")
        return {"success": False, "error": "No current weather data found"}
    
    weather_info = lives[0]
    result = {
        "success": True,
        "type": "current_weather",
        "province": weather_info.get('province'),
        "city": weather_info.get('city'),
        "weather": weather_info.get('weather'),
        "temperature": f"{weather_info.get('temperature', 'N/A')}°C",
        "wind_direction": weather_info.get('winddirection'),
        "wind_power": weather_info.get('windpower'),
        "humidity": f"{weather_info.get('humidity', 'N/A')}%",
        "report_time": weather_info.get('reporttime')
    }
    
    logger.info(f"Current weather for {city}: {weather_info.get('weather')} {weather_info.get('temperature')}°C")
    return result

@mcp.tool()
def get_weather_forecast(city: str, days: int = 4) -> dict:
    """
    Get weather forecast for specified city.
    
    Args:
        city: City name or adcode (e.g., Beijing, 110000)
        days: Number of forecast days (1-4, default: 4)
    
    Returns:
        Dictionary containing weather forecast information
    """
    logger.info(f"Getting weather forecast for: {city} ({days} days)")
    
    # Validate days parameter
    if days < 1 or days > 4:
        days = 4
        logger.warning("Days parameter adjusted to 4 (valid range: 1-4)")
    
    # Check API key
    if not _get_api_key():
        return {"success": False, "error": "AMAP_API_KEY not configured"}
    
    # Make API request
    data = _make_weather_request(city, "all")
    if not data:
        return {"success": False, "error": "Failed to fetch forecast data"}
    
    # Parse response
    if data.get('status') != '1':
        error_msg = data.get('info', 'Unknown API error')
        logger.error(f"API error for {city}: {error_msg}")
        return {"success": False, "error": f"API error: {error_msg}"}
    
    # Extract forecast data
    forecasts = data.get('forecasts', [])
    if not forecasts:
        logger.warning(f"No forecast data for: {city}")
        return {"success": False, "error": "No forecast data found"}
    
    forecast_info = forecasts[0]
    casts = forecast_info.get('casts', [])[:days]
    
    forecast_list = []
    for cast in casts:
        day_temp = cast.get('daytemp', 'N/A')
        night_temp = cast.get('nighttemp', 'N/A')
        
        forecast_day = {
            "date": cast.get('date'),
            "week": cast.get('week'),
            "day_weather": cast.get('dayweather'),
            "night_weather": cast.get('nightweather'),
            "day_temp": f"{day_temp}°C" if day_temp != 'N/A' else 'N/A',
            "night_temp": f"{night_temp}°C" if night_temp != 'N/A' else 'N/A',
            "temp_range": f"{night_temp}°C ~ {day_temp}°C" if day_temp != 'N/A' and night_temp != 'N/A' else 'N/A',
            "day_wind_direction": cast.get('daywind'),
            "night_wind_direction": cast.get('nightwind'),
            "day_wind_power": cast.get('daypower'),
            "night_wind_power": cast.get('nightpower')
        }
        forecast_list.append(forecast_day)
    
    result = {
        "success": True,
        "type": "weather_forecast",
        "province": forecast_info.get('province'),
        "city": forecast_info.get('city'),
        "forecast_days": len(forecast_list),
        "forecasts": forecast_list
    }
    
    logger.info(f"Weather forecast for {city}: {len(forecast_list)} days")
    return result

@mcp.tool()
def get_city_adcode(city_name: str) -> dict:
    """
    Get city adcode (administrative division code) by city name.
    
    Args:
        city_name: City name (e.g., Beijing, Shanghai)
    
    Returns:
        Dictionary containing city adcode information
    """
    logger.info(f"Getting adcode for: {city_name}")
    
    # Check API key
    api_key = _get_api_key()
    if not api_key:
        return {"success": False, "error": "AMAP_API_KEY not configured"}
    
    # Make geocoding request
    url = "https://restapi.amap.com/v3/geocode/geo"
    params = {
        'key': api_key,
        'address': city_name
    }
    
    try:
        logger.info(f"Requesting geocoding for: {city_name}")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Geocoding request failed for {city_name}: {e}")
        return {"success": False, "error": f"Request failed: {str(e)}"}
    
    # Parse response
    if data.get('status') != '1' or not data.get('geocodes'):
        logger.warning(f"City not found: {city_name}")
        return {"success": False, "error": f"City not found: {city_name}"}
    
    geocode = data['geocodes'][0]
    result = {
        "success": True,
        "city": geocode.get('formatted_address'),
        "adcode": geocode.get('adcode'),
        "location": geocode.get('location'),
        "level": geocode.get('level')
    }
    
    logger.info(f"Adcode for {city_name}: {geocode.get('adcode')}")
    return result

# Start server
if __name__ == "__main__":
    logger.info("Weather MCP Server starting...")
    mcp.run(transport="stdio")