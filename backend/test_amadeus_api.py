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
FLIGHT_SEARCH_URL = "https://test.api.amadeus.com/v2/reference-data/urls/checkin-links"

# Get Amadeus API credentials from environment variables
data = {
    "grant_type": "client_credentials",
    "client_id": os.getenv('AMADEUS_API_KEY'),
    "client_secret": os.getenv('AMADEUS_API_SECRET')
}

# Request access token
response = requests.post(AUTH_ENDPOINT, headers={"Content-Type": "application/x-www-form-urlencoded"}, data=data)
response.raise_for_status()  # Raise exception if request fails
access_token = response.json().get('access_token')

if not access_token:
    raise Exception("Failed to get access token from Amadeus API")

# Create SSL context using certifi to handle SSL verification
ssl_context = ssl.create_default_context(cafile=certifi.where())

async def main():
    headers = {'Authorization': f'Bearer {access_token}'}
    parameters = {"airlineCode": 'BA'}  # Example for British Airways

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=ssl_context)) as session:
        for number in range(20):
            async with session.get(
                FLIGHT_SEARCH_URL,
                params=parameters,
                headers=headers
            ) as resp:
                if resp.status == 200:
                    flights = await resp.json()
                    print(f"Flight {number + 1}: {flights}")
                else:
                    print(f"Failed to fetch flight {number + 1}: {resp.status}")

# Run the async function
if __name__ == "__main__":
    asyncio.run(main())
