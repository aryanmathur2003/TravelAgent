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
# AMADEUS_FLIGHT_CHECKIN_URL = "https://test.api.amadeus.com/v2/reference-data/urls/checkin-links"
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
                return format_flight_response(data)
                # return data
            else:
                print(f"❌ Flight search failed: {data}")
                return data
            
def format_flight_response(flight_data):
    """Formats the flight search results into the required structure."""
    if "data" not in flight_data or not flight_data["data"]:
        return "❌ No flights found. Try a different search."

    response_text = "---\n✈️ **Flight Search Results**:\n\n"

    for flight in flight_data["data"]:
        response_text += (
            f"**From:** {flight['origin']} → **To:** {flight['destination']}\n"
            f"**Departure Date:** {flight['departureDate']}\n"
            f"**Price:** ${flight['price']['total']} {flight_data['meta']['currency']}\n"
            "---\n"
        )

    return response_text
