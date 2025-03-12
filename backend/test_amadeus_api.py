import os
import aiohttp
import asyncio
import requests
import ssl
import certifi
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env')

# Amadeus API Credentials
AUTH_ENDPOINT = "https://test.api.amadeus.com/v1/security/oauth2/token"
FLIGHT_DESTINATIONS_URL = "https://test.api.amadeus.com/v1/shopping/flight-destinations"

# Get Amadeus API credentials from environment variables
data = {
    "grant_type": "client_credentials",
    "client_id": os.getenv('AMADEUS_API_KEY'),
    "client_secret": os.getenv('AMADEUS_API_SECRET')
}

# Request access token
response = requests.post(AUTH_ENDPOINT, headers={"Content-Type": "application/x-www-form-urlencoded"}, data=data)
response.raise_for_status()
access_token = response.json().get('access_token')

if not access_token:
    raise Exception("Failed to get access token from Amadeus API")

# Create SSL context using certifi to handle SSL verification
ssl_context = ssl.create_default_context(cafile=certifi.where())

# ✅ Test Parameters
ORIGIN = "PAR"  # Example: Los Angeles International Airport
MAX_PRICE = 500

# ✅ Function to search destinations
async def search_destinations():
    headers = {'Authorization': f'Bearer {access_token}'}
    params = {
        "origin": ORIGIN.upper(),
        "maxPrice": str(MAX_PRICE)
    }

    print(f"🔎 Searching for destinations from {ORIGIN} under ${MAX_PRICE}...")
    print(f"📡 Sending request with params: {params}")

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
        async with session.get(FLIGHT_DESTINATIONS_URL, params=params, headers=headers) as resp:
            data = await resp.json()
            print(f"📡 Response status: {resp.status} - {data}")

            if resp.status == 200:
                destinations = data.get('data', [])
                if not destinations:
                    print("❌ No destinations found.")
                else:
                    print(f"✅ Found {len(destinations)} destinations:\n")
                    for i, destination in enumerate(destinations[:5], 1):
                        print(
                            f"🌍 Destination {i}:\n"
                            f"From: {ORIGIN} → To: {destination['destination']}\n"
                            f"Departure Date: {destination.get('departureDate', 'N/A')}\n"
                            f"Return Date: {destination.get('returnDate', 'N/A')}\n"
                            f"Price: ${destination['price']['total']}\n"
                            f"---"
                        )
            else:
                error = await resp.json()
                print(f"❌ Failed to fetch destinations: {resp.status} - {error}")

# ✅ Run the async function
if __name__ == "__main__":
    asyncio.run(search_destinations())
