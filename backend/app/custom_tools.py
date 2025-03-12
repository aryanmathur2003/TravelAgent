import os
import json
import aiohttp
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
AMADEUS_API_KEY = os.getenv("AMADEUS_API_KEY")
AMADEUS_API_SECRET = os.getenv("AMADEUS_API_SECRET")
AUTH_ENDPOINT = "https://test.api.amadeus.com/v1/security/oauth2/token"
FLIGHT_SEARCH_URL = "https://test.api.amadeus.com/v2/shopping/flight-offers"
BOOKING_URL = "https://test.api.amadeus.com/v1/booking/flight-orders"
flight_cache = {}

# ✅ 1. Get Access Token (Fixed for Async and SSL)
async def get_access_token():
    try:
        logger.info("🔑 Getting access token...")
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "client_credentials",
            "client_id": AMADEUS_API_KEY,
            "client_secret": AMADEUS_API_SECRET
        }

        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
            async with session.post(AUTH_ENDPOINT, headers=headers, data=data) as response:
                if response.status != 200:
                    logger.error(f"❌ Failed to get access token: {response.status} - {await response.text()}")
                    raise Exception(f"Failed to get access token: {response.status} - {await response.text()}")

                token = (await response.json()).get("access_token")

                if not token:
                    raise Exception("Failed to retrieve access token.")
                
                logger.info("✅ Access token received.")
                return token

    except Exception as e:
        logger.error(f"❌ Failed to get access token: {str(e)}", exc_info=True)
        raise


async def search_flights(origin=None, destination=None, departure_date=None, max_price=None):
    try:
        logger.info(f"✈️ Searching flights: origin={origin}, destination={destination}, departure_date={departure_date}, max_price={max_price}")

        if not origin or not destination or not departure_date:
            return {"status": "error", "message": "Missing required flight search parameters."}

        token = await get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        params = {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": departure_date,
            "adults": 1
        }
        if max_price:
            params["maxPrice"] = str(max_price)

        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
            async with session.get(FLIGHT_SEARCH_URL, headers=headers, params=params) as response:
                data = await response.json()

                if response.status != 200:
                    logger.error(f"❌ Flight search failed: {data}")
                    return {"status": "error", "message": f"Failed to search for flights: {data.get('errors', data)}"}

                if not data.get('data'):
                    logger.info("❌ No flights found.")
                    return {"status": "empty", "message": "No flights available for the specified criteria."}

                logger.info(f"✅ Flight search successful! Found {len(data['data'])} flights.")

                # ✅ Store the full object in cache (keyed by flight ID)
                for flight in data["data"]:
                    flight_cache[flight["id"]] = flight

                # ✅ Return simplified info only (no token overload)
                relevant_flights = [
                    {
                        "booking_id": flight["id"],   # ✅ Keep the real ID for booking
                        "airline": flight["validatingAirlineCodes"][0],
                        "price": flight["price"]["total"],
                        "currency": flight["price"]["currency"],
                        "departure": flight["itineraries"][0]["segments"][0]["departure"]["iataCode"],
                        "arrival": flight["itineraries"][0]["segments"][-1]["arrival"]["iataCode"],
                        "departureTime": flight["itineraries"][0]["segments"][0]["departure"]["at"],
                        "arrivalTime": flight["itineraries"][0]["segments"][-1]["arrival"]["at"],
                        "duration": format_duration(flight["itineraries"][0]["duration"]),
                        "stops": len(flight["itineraries"][0]["segments"]) - 1,
                        "cabin": flight["travelerPricings"][0]["fareDetailsBySegment"][0]["cabin"],
                    }
                    for flight in data["data"]
]
                return {"status": "success", "flights": relevant_flights}

    except Exception as e:
        logger.error(f"❌ Unexpected error during flight search: {str(e)}", exc_info=True)
        return {"status": "error", "message": "We are currently unable to process your request. Please contact an agent or try again later."}


# # ✅ 3. Format Flight Results
# def format_flight_response(flight_data):
#     """Format flight search response for user."""
#     logger.info("🔎 Formatting flight search response...")

#     if not flight_data:
#         return "❌ No flights available for the specified criteria."

#     response_text = "---\n✈️ **Flight Search Results**:\n\n"
#     for index, flight in enumerate(flight_data[:5], start=1):
#         itinerary = flight["itineraries"][0]
#         segments = itinerary["segments"][0]
#         response_text += (
#             f"**{index}.** From **{segments['departure']['iataCode']}** "
#             f"to **{segments['arrival']['iataCode']}**\n"
#             f"➡️ Departure: {format_date(segments['departure']['at'])}\n"
#             f"➡️ Arrival: {format_date(segments['arrival']['at'])}\n"
#             f"➡️ Duration: {format_duration(itinerary['duration'])}\n"
#             f"💰 Price: {flight['price']['total']} {flight['price']['currency']}\n"
#             "---\n"
#         )

#     return response_text


async def book_flight(booking_id=None, passenger_name=None):
    try:
        logger.info(f"🛫 Booking flight: booking_id={booking_id}, passenger_name={passenger_name}")

        if not booking_id:
            return {"status": "error", "message": "Missing flight ID. Please select a flight before booking."}
        if not passenger_name:
            return {"status": "error", "message": "Missing passenger name. Please provide the full name of the passenger."}

        # ✅ Retrieve full object from cache using flight ID
        flight = flight_cache.get(booking_id)
        if not flight:
            return {"status": "error", "message": "Flight data expired or missing. Please search again."}

        token = await get_access_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        body = {
            "data": {
                "type": "flight-order",
                "flightOffers": [{
                    "type": flight.get("type", "flight-offer"),
                    "id": flight["id"],
                    "source": flight.get("source", "GDS"),
                    "instantTicketingRequired": flight.get("instantTicketingRequired", False),
                    "nonHomogeneous": flight.get("nonHomogeneous", False),
                    "paymentCardRequired": flight.get("paymentCardRequired", False),  # ✅ Added
                    "lastTicketingDate": flight.get("lastTicketingDate"),
                    "validatingAirlineCodes": flight.get("validatingAirlineCodes", []),
                    "itineraries": [
                        {
                            "segments": [
                                {
                                    "departure": segment["departure"],
                                    "arrival": segment["arrival"],
                                    "carrierCode": segment["carrierCode"],
                                    "number": segment["number"],
                                    "aircraft": segment.get("aircraft", {}),
                                    "duration": segment["duration"],
                                    "id": segment["id"],
                                    "numberOfStops": segment.get("numberOfStops", 0),
                                    "co2Emissions": segment.get("co2Emissions", []),
                                    # ✅ Added missing "operating" field
                                    "operating": segment.get("operating", {"carrierCode": segment["carrierCode"]})
                                }
                                for segment in flight["itineraries"][0]["segments"]
                            ]
                        }
                    ],
                    "price": {
                        "currency": flight["price"]["currency"],
                        "total": flight["price"]["total"],
                        "base": flight["price"]["base"],
                        "fees": flight["price"].get("fees", []),
                        "taxes": flight["travelerPricings"][0]["price"].get("taxes", []),  # ✅ Fixed handling
                        "refundableTaxes": flight["travelerPricings"][0]["price"].get("refundableTaxes", "0.00")
                    },
                    "pricingOptions": flight.get("pricingOptions", {
                        "fareType": ["PUBLISHED"],
                        "includedCheckedBagsOnly": True  # ✅ Fixed value
                    }),
                    "travelerPricings": [
                        {
                            "travelerId": "1",
                            "fareOption": "STANDARD",
                            "travelerType": "ADULT",
                            "price": flight["travelerPricings"][0]["price"],
                            "fareDetailsBySegment": [
                                {
                                    "segmentId": segment["segmentId"],
                                    "cabin": segment["cabin"],
                                    "fareBasis": segment["fareBasis"],
                                    "brandedFare": segment["brandedFare"],
                                    "class": segment["class"],
                                    # ✅ Added includedCheckedBags
                                    "includedCheckedBags": segment.get("includedCheckedBags", {"quantity": 1})
                                }
                                for segment in flight["travelerPricings"][0]["fareDetailsBySegment"]
                            ]
                        }
                    ]
                }],
                "travelers": [
                    {
                        "id": "1",
                        "dateOfBirth": "1990-01-01",
                        "gender": "MALE",
                        "name": {
                            "firstName": passenger_name.split()[0],
                            "lastName": passenger_name.split()[1]
                        },
                        "contact": {
                            "emailAddress": "test@example.com",
                            "phones": [{
                                "deviceType": "MOBILE",
                                "countryCallingCode": "1",
                                "number": "5551234567"
                            }]
                        },
                        "documents": [{
                            "documentType": "PASSPORT",
                            "birthPlace": "New York",
                            "issuanceLocation": "New York",
                            "issuanceDate": "2015-04-14",
                            "number": "00000000",
                            "expiryDate": "2025-04-14",
                            "issuanceCountry": "US",
                            "validityCountry": "US",
                            "nationality": "US",
                            "holder": True
                        }]
                    }
                ],
                "ticketingAgreement": {
                    "option": "DELAY_TO_CANCEL",  # ✅ Fixed value
                    "delay": "6D"
                },
                "contacts": [{
                    "addresseeName": {
                        "firstName": passenger_name.split()[0],
                        "lastName": passenger_name.split()[1]
                    },
                    "companyName": "Travel Inc.",
                    "purpose": "STANDARD",
                    "phones": [{
                        "deviceType": "LANDLINE",
                        "countryCallingCode": "1",
                        "number": "5551234567"
                    }],
                    "emailAddress": "support@travelinc.com",
                    "address": {
                        "lines": ["123 Main St"],
                        "postalCode": "10001",
                        "cityName": "New York",
                        "countryCode": "US"
                    }
                }]
            }
        }

        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
            async with session.post(BOOKING_URL, headers=headers, json=body) as response:
                data = await response.json()

                if response.status != 201:
                    logger.error(f"❌ Booking failed: {data}")
                    return {"status": "error", "message": f"Failed to book flight: {data.get('errors', data)}"}

                logger.info("✅ Booking successful!")
                return f"✅ Booking Confirmed! Booking ID: {data['data']['id']}"

    except Exception as e:
        logger.error(f"❌ Unexpected error during flight booking: {str(e)}", exc_info=True)
        return {"status": "error", "message": "We are currently unable to process your request. Please contact an agent or try again later."}


# ✅ 5. Format Duration
def format_duration(duration):
    if duration.startswith("PT"):
        duration = duration[2:]
        hours = minutes = 0
        if "H" in duration:
            hours, duration = duration.split("H")
            hours = int(hours)
        if "M" in duration:
            minutes = int(duration.replace("M", ""))
        return f"{hours}h {minutes}m" if hours else f"{minutes}m"
    return duration


# ✅ 6. Format Date
def format_date(date_str):
    try:
        date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S")
        return date.strftime("%A, %B %d, %Y at %I:%M %p")
    except Exception:
        return date_str
