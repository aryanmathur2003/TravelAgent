import os
import json
import aiohttp
import logging
from datetime import datetime

# ✅ Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ✅ Load environment variables
AMADEUS_API_KEY = os.getenv("AMADEUS_API_KEY")
AMADEUS_API_SECRET = os.getenv("AMADEUS_API_SECRET")

# ✅ Define Endpoints
AUTH_ENDPOINT = "https://test.api.amadeus.com/v1/security/oauth2/token"
HOTEL_BY_CITY_URL = "https://test.api.amadeus.com/v1/reference-data/locations/hotels/by-city"
HOTEL_BY_HOTEL_ID_URL = "https://test.api.amadeus.com/v1/reference-data/locations/hotels/by-hotels"
HOTEL_BY_GEOCODE_URL = "https://test.api.amadeus.com/v1/reference-data/locations/hotels/by-geocode"
HOTEL_BOOKING_URL = "https://test.api.amadeus.com/v2/booking/hotel-orders"
HOTEL_OFFERS_URL = "https://test.api.amadeus.com/v3/shopping/hotel-offers"


# ✅ Cache to store hotel offers temporarily (keyed by offer ID)
hotel_cache = {}
BATCH_SIZE = 5

# ✅ 1. Get Access Token (Fixed for Async and SSL)
async def get_access_token():
    try:
        logger.info("🔑 Getting access token for Amadeus...")
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

# ✅ 2. Search Hotels
async def search_hotels(city_code=None, latitude=None, longitude=None, hotel_ids=None):
    global hotel_pointer

    try:
        logger.info(f"🏨 Searching hotels: city_code={city_code}, latitude={latitude}, longitude={longitude}, hotel_ids={hotel_ids}")

        if not hotel_ids and not latitude and not longitude and not city_code:
            return {"status": "error", "message": "Please provide city code, geocode, or hotel ID."}

        token = await get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        params = {}

        if hotel_ids:
            url = HOTEL_BY_HOTEL_ID_URL
            params["hotelIds"] = ",".join(hotel_ids)
        elif latitude and longitude:
            url = HOTEL_BY_GEOCODE_URL
            params = {
                "latitude": latitude,
                "longitude": longitude,
                "radius": 5,
                "radiusUnit": "KM"
            }
        elif city_code:
            if len(city_code) != 3:
                return {"status": "error", "message": f"Invalid city code: '{city_code}'. Provide a valid 3-letter IATA city code (e.g., 'SFO')."}
            url = HOTEL_BY_CITY_URL
            params = {
                "cityCode": city_code,
                "radius": 5,
                "radiusUnit": "KM"
            }

        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
            async with session.get(url, headers=headers, params=params) as response:
                data = await response.json()

                if response.status != 200:
                    logger.error(f"❌ Hotel search failed: {data}")
                    return {"status": "error", "message": f"Failed to search for hotels: {data.get('errors', data)}"}

                if not data.get('data'):
                    logger.info("❌ No hotels found.")
                    return {"status": "empty", "message": "No hotels available for the specified criteria."}

                logger.info(f"✅ Hotel search successful! Found {len(data['data'])} hotels.")

                # ✅ Cache the full list
                hotel_cache.clear()
                hotel_cache.update({hotel["hotelId"]: hotel for hotel in data["data"]})
                hotel_pointer = 0

                return await get_next_hotel_results()

    except Exception as e:
        logger.error(f"❌ Unexpected error during hotel search: {str(e)}", exc_info=True)
        return {"status": "error", "message": "We are currently unable to process your request. Please contact an agent or try again later."}

# ✅ 3. Get Next Results (Pagination)
async def get_next_hotel_results():
    global hotel_pointer

    if hotel_pointer >= len(hotel_cache):
        return {"status": "empty", "message": "No more hotels available."}

    hotels_to_send = list(hotel_cache.values())[hotel_pointer : hotel_pointer + BATCH_SIZE]
    hotel_pointer += len(hotels_to_send)

    formatted_hotels = [
        {
            "hotel_id": hotel["hotelId"],
            "name": hotel.get("name", "Unknown"),
            "city": hotel.get("cityCode", "Unknown"),
            "latitude": hotel.get("geoCode", {}).get("latitude"),
            "longitude": hotel.get("geoCode", {}).get("longitude"),
            "distance": hotel.get("distance", {}).get("value"),
        }
        for hotel in hotels_to_send
    ]

    return {"status": "success", "hotels": formatted_hotels}

# ✅ 4. Search Hotel Offers
from datetime import datetime, timedelta

async def search_hotel_offers(hotel_ids, check_in_date, check_out_date, adults):
    try:
        logger.info(f"🔍 Searching hotel offers for hotel_id={hotel_ids}...")

        if not hotel_ids:
            return {"status": "error", "message": "Missing hotel IDs."}
        if not check_in_date or not check_out_date:
            return {"status": "error", "message": "Missing check-in or check-out date."}
        
        if not check_in_date or not check_out_date:
            return {"status": "error", "message": "Please provide valid check-in and check-out dates."}

        today = datetime.today().strftime("%Y-%m-%d")
        if check_in_date < today:
            return {"status": "error", "message": "Check-in date must be in the future."}
        if check_out_date <= check_in_date:
            return {"status": "error", "message": "Check-out date must be after the check-in date."}


        token = await get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        params = {
            "hotelIds": hotel_ids,
            "checkInDate": check_in_date or datetime.today().strftime("%Y-%m-%d"),
            "checkOutDate": check_out_date or (datetime.today().strftime("%Y-%m-%d")),
            "adults": adults or 1
        }

        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
            async with session.get(HOTEL_OFFERS_URL, headers=headers, params=params) as response:
                data = await response.json()

                if response.status != 200:
                    logger.error(f"❌ Failed to retrieve hotel offers: {data}")
                    return {"status": "error", "message": f"Failed to get offers: {data.get('errors', data)}"}

                if not data.get('data'):
                    logger.info("❌ No offers found.")
                    return {"status": "empty", "message": "No available offers for the selected hotels."}

                logger.info(f"✅ Hotel offers retrieved for {len(data['data'])} hotels.")

                # ✅ Format offers and ensure 'total' is available
                offers = []
                for offer in data["data"]:
                    try:
                        offer_id = offer["offers"][0].get("id", "N/A")
                        price = offer["offers"][0].get("price", {}).get("total", "N/A")
                        currency = offer["offers"][0].get("price", {}).get("currency", "N/A")

                        formatted_offer = {
                            "offer_id": offer_id,  # ✅ Keep offer ID
                            "hotel_id": offer["hotel"]["hotelId"],
                            "name": offer["hotel"]["name"],
                            "city": offer["hotel"]["cityCode"],
                            "checkInDate": offer["offers"][0].get("checkInDate", "N/A"),
                            "checkOutDate": offer["offers"][0].get("checkOutDate", "N/A"),
                            "price": price if price != "N/A" else "Not Available",
                            "currency": currency if currency != "N/A" else "Not Available",
                            "room_type": offer["offers"][0]["room"]["description"].get("text", "N/A"),
                            "payment_policy": offer["offers"][0]["policies"].get("paymentType", "N/A")
                        }
                        offers.append(formatted_offer)

                    except Exception as e:
                        logger.error(f"❌ Error while formatting offer: {str(e)}")

                if not offers:
                    return {"status": "empty", "message": "No available offers for the selected hotels."}

                # ✅ Return structured result with offer IDs
                response_text = "Here are the available offers:\n\n"
                for idx, offer in enumerate(offers, 1):
                    response_text += (
                        f"**{idx}. {offer['name']}**\n"
                        f"➡️ **Offer ID:** `{offer['offer_id']}`\n"  # ✅ Show offer ID explicitly
                        f"➡️ **Room Type:** {offer['room_type']}\n"
                        f"➡️ **Price:** {offer['price']} {offer['currency']}\n"
                        f"➡️ **Payment Policy:** {offer['payment_policy']}\n"
                        "---\n"
                    )

                return {
                    "status": "success",
                    "offers": offers,
                    "message": response_text
                }

    except Exception as e:
        logger.error(f"❌ Error while searching hotel offers: {str(e)}", exc_info=True)
        return {"status": "error", "message": "We are currently unable to process your request. Please contact an agent or try again later."}


async def book_hotel(offer_id=None, guests=None):
    try:
        logger.info(f"🏨 Booking hotel: offer_id={offer_id}, guests={guests}")

        if not offer_id:
            return {"status": "error", "message": "Missing hotel offer ID. Please select a hotel before booking."}
        if not guests:
            return {"status": "error", "message": "Missing guest information."}

        token = await get_access_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        body = {
            "data": {
                "type": "hotel-order",
                "guests": guests,
                "roomAssociations": [
                    {
                        "guestReferences": [{"guestReference": str(index + 1)} for index in range(len(guests))],
                        "hotelOfferId": offer_id
                    }
                ],
                "travelAgent": {
                    "contact": {"email": guests[0]["email"]}
                },
                "payment": {
                    "method": "CREDIT_CARD",
                    "paymentCard": {
                        "paymentCardInfo": {
                            "vendorCode": "VI",
                            "cardNumber": "4151289722471370",  # Test Card
                            "expiryDate": "2026-08",
                            "holderName": guests[0]["firstName"] + " " + guests[0]["lastName"]
                        }
                    }
                }
            }
        }

        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
            async with session.post(HOTEL_BOOKING_URL, headers=headers, json=body) as response:
                data = await response.json()

                if response.status != 201:
                    logger.error(f"❌ Booking failed: {data}")
                    return {"status": "error", "message": f"Failed to book hotel: {data.get('errors', data)}"}

                logger.info(f"✅ Hotel booking successful! Booking ID: {data['data']['id']}")
                return {"status": "success", "booking_id": data["data"]["id"]}

    except Exception as e:
        logger.error(f"❌ Error during hotel booking: {str(e)}", exc_info=True)
        return {"status": "error", "message": "We are currently unable to process your request. Please contact an agent or try again later."}

# ✅ 4. Format Date (Helper)
def format_date(date_str):
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d")
        return date.strftime("%A, %B %d, %Y")
    except Exception:
        return date_str

# ✅ 5. Format Price (Helper)
def format_price(price, currency):
    return f"{price} {currency}"

