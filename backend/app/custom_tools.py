"""
Implement the Amadeus API integration here by creating custom tools. 
"""
import json
import aiohttp
import asyncio
import os 
from dotenv import load_dotenv
import logging
import requests

logger = logging.getLogger(__name__)

load_dotenv('.env') 
# Configure logging
logging.basicConfig(level=logging.INFO)


# Amadeus API Credentials
AMADEUS_API_KEY = os.getenv("AMADEUS_API_KEY")
AMADEUS_API_SECRET = os.getenv("AMADEUS_API_SECRET")
AUTH_ENDPOINT = "https://test.api.amadeus.com/v1/security/oauth2/token"
AMADEUS_FLIGHT_CHECKIN_URL = "https://test.api.amadeus.com/v2/reference-data/urls/checkin-links"
FLIGHT_SEARCH_URL = "https://test.api.amadeus.com/v1/shopping/flight-destinations"

def get_access_token():
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "client_id": AMADEUS_API_KEY,
        "client_secret": AMADEUS_API_SECRET
    }
    response = requests.post(AUTH_ENDPOINT, headers=headers, data=data)
    return response.json().get("access_token")

# 2️⃣ Search for Flights
async def search_flights(origin: str, max_price: int):
    """Search flights"""
    token = get_access_token()
    if not token:
        print("❌ Failed to get access token.")
        return {"error": "Authentication failed."}

    headers = {"Authorization": f"Bearer {token}"}
    params = {"origin": origin, "maxPrice": str(max_price)}

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
        async with session.get(FLIGHT_SEARCH_URL, headers=headers, params=params) as response:
            data = await response.json()

            if response.status == 200:
                print("✅ Flight search successful!")
                return data
            else:
                print(f"❌ Flight search failed: {data}")
                return data

async def get_weather(location: str, units: str = "metric"):
    """
    Get current weather for a location.
    
    Args:
        location: City name or geographic coordinates
        units: Units of measurement (metric, imperial, standard)
    
    Returns:
        Weather information for the specified location
    """
    # This is a mock implementation - in a real app, you would call a weather API
    await asyncio.sleep(1)  # Simulate API call
    
    return {
        "location": location,
        "temperature": 22.5 if units == "metric" else 72.5,
        "conditions": "Partly cloudy",
        "humidity": 65,
        "wind_speed": 10,
        "units": units
    }


def calculate(expression: str):
    """
    Evaluate a mathematical expression.
    
    Args:
        expression: A mathematical expression as string (e.g. "2 + 2")
    
    Returns:
        The result of the calculation
    """
    # Be careful with eval - this is just for demonstration
    # In production, use a safer approach or a math expression parser
    try:
        # Restrict to safe operations
        allowed_names = {"abs": abs, "round": round, "min": min, "max": max}
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}


async def search_wikipedia(query: str, limit: int = 3):
    """
    Search Wikipedia for information.
    
    Args:
        query: Search term
        limit: Maximum number of results to return
    
    Returns:
        Search results from Wikipedia
    """
    async with aiohttp.ClientSession() as session:
        # This would be a real Wikipedia API call in production
        await asyncio.sleep(1)  # Simulate API call
        
        return {
            "query": query,
            "results": [
                {
                    "title": f"{query} - Primary result",
                    "snippet": f"This is information about {query}...",
                    "url": f"https://en.wikipedia.org/wiki/{query.replace(' ', '_')}"
                },
                {
                    "title": f"{query} - Related topic",
                    "snippet": f"Related information to {query}...",
                    "url": f"https://en.wikipedia.org/wiki/Related_{query.replace(' ', '_')}"
                }
            ][:limit]
        } 