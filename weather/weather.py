from mcp.server.fastmcp import FastMCP
import sys
from loguru import logger
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure loguru logger to output to stderr (same as calculator.py)
logger.remove()  # Remove default handler
logger.add(sys.stderr, format="{time:YYYY-MM-DD HH:mm:ss} | {level} | Weather | {message}", level="INFO")

# Fix UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stderr.reconfigure(encoding='utf-8')
    sys.stdout.reconfigure(encoding='utf-8')

# Create an MCP server
mcp = FastMCP("Weather")

@mcp.tool()
def get_weather(city: str, extensions: str = "base") -> dict:
    """
    Query weather information for specified city
    
    Args:
        city: City name or adcode, e.g.: Beijing, 110000
        extensions: Weather type, base=current weather, all=forecast weather, default is base
    
    Returns:
        Dictionary containing weather information
    """
    logger.info(f"Weather query started: {city} (type: {extensions})")
    
    try:
        # Get Amap API Key from environment variables
        api_key = os.getenv('AMAP_API_KEY')
        if not api_key:
            logger.error("AMAP_API_KEY environment variable not set")
            return {"success": False, "error": "Please set AMAP_API_KEY environment variable"}
        
        # Amap weather query API URL
        url = "https://restapi.amap.com/v3/weather/weatherInfo"
        
        params = {
            'key': api_key,
            'city': city,
            'extensions': extensions
        }
        
        logger.info(f"Sending API request for: {city}")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"API response received for: {city}")
        
        if data.get('status') == '1':
            if extensions == 'base':
                # Current weather
                if data.get('lives'):
                    weather_info = data['lives'][0]
                    result = {
                        "success": True,
                        "type": "Current Weather",
                        "province": weather_info.get('province'),
                        "city": weather_info.get('city'),
                        "weather": weather_info.get('weather'),
                        "temperature": weather_info.get('temperature') + "°C",
                        "wind_direction": weather_info.get('winddirection'),
                        "wind_power": weather_info.get('windpower'),
                        "humidity": weather_info.get('humidity') + "%",
                        "report_time": weather_info.get('reporttime')
                    }
                    logger.info(f"Weather result: {city} - {weather_info.get('weather')} {weather_info.get('temperature')}°C")
                else:
                    logger.warning(f"No weather data found for: {city}")
                    result = {"success": False, "error": "Weather data not found"}
            else:
                # Forecast weather
                if data.get('forecasts'):
                    forecast_info = data['forecasts'][0]
                    casts = forecast_info.get('casts', [])
                    
                    forecast_list = []
                    for cast in casts:
                        forecast_list.append({
                            "date": cast.get('date'),
                            "week": cast.get('week'),
                            "day_weather": cast.get('dayweather'),
                            "night_weather": cast.get('nightweather'),
                            "day_temp": cast.get('daytemp') + "°C",
                            "night_temp": cast.get('nighttemp') + "°C",
                            "day_wind": cast.get('daywind'),
                            "night_wind": cast.get('nightwind'),
                            "day_power": cast.get('daypower'),
                            "night_power": cast.get('nightpower')
                        })
                    
                    result = {
                        "success": True,
                        "type": "Forecast Weather",
                        "province": forecast_info.get('province'),
                        "city": forecast_info.get('city'),
                        "forecasts": forecast_list
                    }
                    logger.info(f"Forecast result: {city} - {len(forecast_list)} days forecast")
                else:
                    logger.warning(f"No forecast data found for: {city}")
                    result = {"success": False, "error": "Forecast data not found"}
        else:
            error_info = data.get('info', 'Unknown error')
            logger.error(f"API error for {city}: {error_info}")
            result = {"success": False, "error": f"API error: {error_info}"}
        
        logger.info(f"Weather query completed for: {city}")
        return result
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Network request error: {str(e)}"
        logger.error(f"Network error for {city}: {error_msg}")
        return {"success": False, "error": error_msg}
    except Exception as e:
        error_msg = f"Error occurred while querying weather: {str(e)}"
        logger.error(f"Unexpected error for {city}: {error_msg}")
        return {"success": False, "error": error_msg}

@mcp.tool()
def get_city_adcode(city_name: str) -> dict:
    """
    Get adcode (administrative division code) based on city name
    
    Args:
        city_name: City name, e.g.: Beijing, Shanghai
    
    Returns:
        Dictionary containing city adcode information
    """
    logger.info(f"Adcode query started: {city_name}")
    
    try:
        api_key = os.getenv('AMAP_API_KEY')
        if not api_key:
            logger.error("AMAP_API_KEY environment variable not set")
            return {"success": False, "error": "Please set AMAP_API_KEY environment variable"}
        
        # Amap geocoding API
        url = "https://restapi.amap.com/v3/geocode/geo"
        
        params = {
            'key': api_key,
            'address': city_name
        }
        
        logger.info(f"Sending geocoding request for: {city_name}")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"Geocoding response received for: {city_name}")
        
        if data.get('status') == '1' and data.get('geocodes'):
            geocode = data['geocodes'][0]
            result = {
                "success": True,
                "city": geocode.get('formatted_address'),
                "adcode": geocode.get('adcode'),
                "location": geocode.get('location'),
                "level": geocode.get('level')
            }
            logger.info(f"Adcode result: {city_name} -> {geocode.get('adcode')}")
        else:
            logger.warning(f"City not found: {city_name}")
            result = {"success": False, "error": f"City not found: {city_name}"}
        
        logger.info(f"Adcode query completed for: {city_name}")
        return result
        
    except Exception as e:
        error_msg = f"Error occurred while querying city adcode: {str(e)}"
        logger.error(f"Error querying adcode for {city_name}: {error_msg}")
        return {"success": False, "error": error_msg}

# Start the server
if __name__ == "__main__":
    logger.info("Weather MCP Server starting...")
    mcp.run(transport="stdio")