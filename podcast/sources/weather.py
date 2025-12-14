"""Weather data fetching using Open-Meteo API (free, no API key required)."""

import requests
from datetime import datetime
from typing import Optional


# Weather code descriptions for Open-Meteo
WEATHER_CODES = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "foggy",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "moderate drizzle",
    55: "dense drizzle",
    56: "light freezing drizzle",
    57: "dense freezing drizzle",
    61: "slight rain",
    63: "moderate rain",
    65: "heavy rain",
    66: "light freezing rain",
    67: "heavy freezing rain",
    71: "slight snow",
    73: "moderate snow",
    75: "heavy snow",
    77: "snow grains",
    80: "slight rain showers",
    81: "moderate rain showers",
    82: "violent rain showers",
    85: "slight snow showers",
    86: "heavy snow showers",
    95: "thunderstorm",
    96: "thunderstorm with slight hail",
    99: "thunderstorm with heavy hail",
}


def fetch_weather(
    lat: float,
    lon: float,
    units: str = "fahrenheit",
    include_forecast: bool = True,
    forecast_days: int = 1,
) -> Optional[dict]:
    """Fetch weather data from Open-Meteo API.
    
    Args:
        lat: Latitude of the location.
        lon: Longitude of the location.
        units: Temperature units - "fahrenheit" or "celsius".
        include_forecast: Whether to include forecast data.
        forecast_days: Number of forecast days (1-7).
    
    Returns:
        Dictionary with weather data, or None if request fails.
    """
    # Build API URL
    base_url = "https://api.open-meteo.com/v1/forecast"
    
    temp_unit = "fahrenheit" if units == "fahrenheit" else "celsius"
    
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
        "temperature_unit": temp_unit,
        "wind_speed_unit": "mph",
        "timezone": "auto",
    }
    
    if include_forecast:
        params["daily"] = "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
        params["forecast_days"] = min(forecast_days, 7)
    
    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        return _parse_weather_response(data, units)
    
    except requests.RequestException as e:
        print(f"Weather API error: {e}")
        return None


def _parse_weather_response(data: dict, units: str) -> dict:
    """Parse Open-Meteo API response into a friendly format."""
    current = data.get("current", {})
    daily = data.get("daily", {})
    
    # Get current conditions
    weather_code = current.get("weather_code", 0)
    condition = WEATHER_CODES.get(weather_code, "unknown conditions")
    
    temp_symbol = "°F" if units == "fahrenheit" else "°C"
    
    result = {
        "current": {
            "temperature": current.get("temperature_2m"),
            "humidity": current.get("relative_humidity_2m"),
            "condition": condition,
            "wind_speed": current.get("wind_speed_10m"),
            "temp_unit": temp_symbol,
        },
        "location": {
            "timezone": data.get("timezone", ""),
        },
        "fetched_at": datetime.now().isoformat(),
    }
    
    # Add forecast if available
    if daily and daily.get("time"):
        forecasts = []
        times = daily.get("time", [])
        codes = daily.get("weather_code", [])
        highs = daily.get("temperature_2m_max", [])
        lows = daily.get("temperature_2m_min", [])
        precip = daily.get("precipitation_probability_max", [])
        
        for i, time in enumerate(times):
            forecast = {
                "date": time,
                "condition": WEATHER_CODES.get(codes[i] if i < len(codes) else 0, "unknown"),
                "high": highs[i] if i < len(highs) else None,
                "low": lows[i] if i < len(lows) else None,
                "precipitation_chance": precip[i] if i < len(precip) else None,
                "temp_unit": temp_symbol,
            }
            forecasts.append(forecast)
        
        result["forecast"] = forecasts
    
    return result


def format_weather_for_script(weather: dict, location_name: str) -> str:
    """Format weather data into a natural language description for the script.
    
    Args:
        weather: Parsed weather data from fetch_weather().
        location_name: Human-readable location name.
    
    Returns:
        A natural language weather description.
    """
    if not weather or not weather.get("current"):
        return f"Weather information for {location_name} is currently unavailable."
    
    current = weather["current"]
    temp = current.get("temperature")
    condition = current.get("condition", "")
    humidity = current.get("humidity")
    unit = current.get("temp_unit", "°F")
    
    # Build current conditions string
    parts = []
    
    if temp is not None:
        parts.append(f"It's currently {temp:.0f}{unit}")
    
    if condition:
        parts.append(f"with {condition}")
    
    if humidity is not None:
        parts.append(f"and {humidity}% humidity")
    
    current_desc = " ".join(parts) if parts else ""
    
    # Add forecast if available
    forecast_desc = ""
    if weather.get("forecast") and len(weather["forecast"]) > 0:
        today = weather["forecast"][0]
        high = today.get("high")
        low = today.get("low")
        precip = today.get("precipitation_chance")
        
        forecast_parts = []
        if high is not None and low is not None:
            forecast_parts.append(f"Today's high will be {high:.0f}{unit}, low of {low:.0f}{unit}")
        
        if precip is not None and precip > 20:
            forecast_parts.append(f"with a {precip}% chance of precipitation")
        
        if forecast_parts:
            forecast_desc = ". " + " ".join(forecast_parts)
    
    return f"In {location_name}: {current_desc}{forecast_desc}."

