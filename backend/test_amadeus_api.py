import requests

AUTH_ENDPOINT = "https://test.api.amadeus.com/v1/security/oauth2/token"
FLIGHT_SEARCH_URL = "https://test.api.amadeus.com/v1/shopping/flight-destinations"

# Amadeus API Credentials
AMADEUS_API_KEY = "BALQTVgsAkj8XI4QHAOyTbzytNYBeCtJ"
AMADEUS_API_SECRET = "z7WXrJh8ca53gY1r"

# 1️⃣ Get Access Token
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
def search_flights(origin, max_price):
    token = get_access_token()
    if not token:
        print("❌ Failed to get access token.")
        return

    headers = {"Authorization": f"Bearer {token}"}
    params = {"origin": origin, "maxPrice": str(max_price)}

    response = requests.get(FLIGHT_SEARCH_URL, headers=headers, params=params, verify=False)

    if response.status_code == 200:
        print("✅ Flight search successful!")
        print(response.json())
    else:
        print(f"❌ Flight search failed: {response.json()}")

# 3️⃣ Run Test
if __name__ == "__main__":
    search_flights("ORD", 1000)
