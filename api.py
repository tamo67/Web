import os
from amadeus import Client, ResponseError

amadeus = Client(
    client_id=os.environ.get("AMADEUS_ID"),
    client_secret=os.environ.get("AMADEUS_SECRET")
)
def get_flight_data_fixed(origin, destination, departure_date):
    try:
        response = amadeus.shopping.flight_offers_search.get(
            originLocationCode=origin,
            destinationLocationCode=destination,
            departureDate=departure_date,
            adults=1,
            max=50
        )
        return response.data
    except ResponseError as error:
        print(f"API Error: {error}")
        return []
