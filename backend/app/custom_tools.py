import os
import json
import aiohttp
import asyncio
import logging
import requests

logger = logging.getLogger(__name__)

# Load environment variables
AMADEUS_API_KEY = os.getenv("AMADEUS_API_KEY")
AMADEUS_API_SECRET = os.getenv("AMADEUS_API_SECRET")
AUTH_ENDPOINT = "https://test.api.amadeus.com/v1/security/oauth2/token"
FLIGHT_SEARCH_URL = "https://test.api.amadeus.com/v2/shopping/flight-offers"
AVAILABILITY_URL = "https://test.api.amadeus.com/v1/schedule/flights"
PRICING_URL = "https://test.api.amadeus.com/v1/shopping/flight-offers/pricing"
BOOKING_URL = "https://test.api.amadeus.com/v1/booking/flight-orders"


# 1️⃣ Get Access Token
def get_access_token():
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "client_id": AMADEUS_API_KEY,
        "client_secret": AMADEUS_API_SECRET
    }
    response = requests.post(AUTH_ENDPOINT, headers=headers, data=data)
    if response.status_code != 200:
        raise Exception(f"Failed to authenticate: {response.status_code} - {response.text}")
    
    return response.json().get("access_token")


# 2️⃣ Search for Flights
async def search_flights(origin: str, destination: str, departure_date: str, max_price: int):
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "originLocationCode": origin,
        "destinationLocationCode": destination,
        "departureDate": departure_date,
        "maxPrice": max_price,
        "adults": 1
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(FLIGHT_SEARCH_URL, headers=headers, params=params) as response:
            data = await response.json()
            if response.status == 200:
                return format_flight_response(data)
            else:
                return f"❌ Flight search failed: {data.get('errors', data)}"


def format_flight_response(flight_data):
    """Format flight search response."""
    if "data" not in flight_data or not flight_data["data"]:
        return "❌ No flights found. Try a different search."

    response_text = "---\n✈️ **Flight Search Results**:\n\n"
    for flight in flight_data["data"][:5]:
        itinerary = flight["itineraries"][0]
        segments = itinerary["segments"][0]
        response_text += (
            f"**From:** {segments['departure']['iataCode']} → {segments['arrival']['iataCode']}\n"
            f"**Departure Date:** {segments['departure']['at']}\n"
            f"**Arrival Date:** {segments['arrival']['at']}\n"
            f"**Price:** ${flight['price']['total']}\n"
            "---\n"
        )

    return response_text


# 3️⃣ Get Flight Availability
async def get_flight_availability(flight_number: str, date: str):
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "carrierCode": flight_number[:2],
        "flightNumber": flight_number[2:],
        "scheduledDepartureDate": date
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(AVAILABILITY_URL, headers=headers, params=params) as response:
            data = await response.json()
            if response.status == 200 and data.get("data"):
                details = data["data"][0]
                return (
                    f"✅ Availability:\n"
                    f"Flight: {details['flightDesignator']['flightNumber']}\n"
                    f"Status: {details.get('flightStatus', 'Unknown')}\n"
                )
            else:
                return f"❌ No availability found: {data.get('errors', data)}"


# 4️⃣ Get Flight Pricing
async def get_flight_pricing(flight_id: str):
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = {"data": {"type": "flight-offer", "id": flight_id}}

    async with aiohttp.ClientSession() as session:
        async with session.post(PRICING_URL, headers=headers, json=body) as response:
            data = await response.json()
            if response.status == 200 and data.get("data"):
                price = data["data"]["price"]
                return (
                    f"✅ Price:\n"
                    f"Total: ${price['total']}\n"
                    f"Currency: {price['currency']}\n"
                )
            else:
                return f"❌ Failed to get pricing: {data.get('errors', data)}"


# 5️⃣ Book a Flight
async def book_flight(flight_id: str, passenger_name: str):
    token = get_access_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = {
        "data": {
            "type": "flight-order",
            "flightOffers": [{"id": flight_id}],
            "travelers": [{
                "id": "1",
                "dateOfBirth": "1990-01-01",
                "name": {
                    "firstName": passenger_name.split()[0],
                    "lastName": passenger_name.split()[1]
                },
                "gender": "MALE",
                "contact": {
                    "emailAddress": "example@example.com",
                    "phones": [{
                        "deviceType": "MOBILE",
                        "countryCallingCode": "1",
                        "number": "5551234567"
                    }]
                }
            }]
        }
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(BOOKING_URL, headers=headers, json=body) as response:
            data = await response.json()
            if response.status == 200 and data.get("data"):
                return f"✅ Booking Confirmed! Booking ID: {data['data']['id']}"
            else:
                return f"❌ Booking failed: {data.get('errors', data)}"
