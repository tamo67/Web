import os
import json
from datetime import datetime
from api import get_flight_data_fixed

with open(os.path.join("Week3", "data.json"), "r") as f:
    redemption_chart = json.load(f)

allowed_airlines = {
    "AA": "American Airlines",
    "BA": "British Airways",
    "SQ": "Singapore Airlines",
    "TG": "Thai Airways",
    "TK": "Turkish Airlines",
    "LH": "Lufthansa"
}

def parse_flights(api_data):
    routes = []
    for i, flight in enumerate(api_data):
        price = float(flight["price"]["total"])
        base = float(flight["price"]["base"])
        taxes = round(price - base, 2)

        for itinerary in flight["itineraries"]:
            segments = itinerary["segments"]
            airlines = list(set(seg["carrierCode"] for seg in segments))
            if not any(a in allowed_airlines for a in airlines):
                continue

            path = [seg["departure"]["iataCode"] for seg in segments]
            path.append(segments[-1]["arrival"]["iataCode"])
            route_str = " → ".join(path)

            route = {
                "id": f"Route-{i+1}",
                "origin": segments[0]["departure"]["iataCode"],
                "destination": segments[-1]["arrival"]["iataCode"],
                "route_str": route_str,
                "airlines": airlines,
                "departure": segments[0]["departure"]["at"],
                "arrival": segments[-1]["arrival"]["at"],
                "duration": itinerary["duration"],
                "price": price,
                "base": base,
                "taxes": taxes,
                "stops": len(segments) - 1
            }
            routes.append(route)
    return routes

def get_miles_required(origin, destination, airline):
    route_key = f"{origin}-{destination}"
    if airline in redemption_chart and route_key in redemption_chart[airline]:
        return redemption_chart[airline][route_key]["ECONOMY"]
    return None

def calculate_vpm(price, taxes, miles_required):
    return round((price - taxes) / miles_required, 4)

def find_optimal_route(routes):
    return sorted(routes, key=lambda r: (r["price"], r["stops"], r["duration"]))[0]

def find_cheapest_with_miles(routes):
    for route in sorted(routes, key=lambda r: r["price"]):
        for airline in route["airlines"]:
            miles = get_miles_required(route["origin"], route["destination"], airline)
            if miles:
                return route, airline, miles
    return None, None, None

def main():
    routes_list = [("JFK", "HEL"), ("SYD", "BKK"), ("IST", "YYZ")]

    print("Available Routes (Only Economy class data because of lack of data for other classes):")
    for i, (origin, dest) in enumerate(routes_list):
        print(f"{i+1}. {origin} → {dest}")

    choice = input("Choose a route by number: ").strip()
    if not choice.isdigit() or int(choice) not in range(1, len(routes_list)+1):
        print("Invalid choice.")
        return

    route_index = int(choice) - 1
    origin, destination = routes_list[route_index]

    departure_date = input("Enter departure date (YYYY-MM-DD): ").strip()
    flights = get_flight_data_fixed(origin, destination, departure_date)
    if not flights:
        print("No flights returned from API.")
        return

    routes = parse_flights(flights)
    if not routes:
        print("No valid flights with allowed airlines.")
        return

    print(f"\nTop 5 Cheapest Routes from {origin} to {destination}:")
    for r in sorted(routes, key=lambda r: r["price"])[:5]:
        print(f"{r['id']} | ${r['price']} (Base: ${r['base']} + Taxes: ${r['taxes']}) | Stops: {r['stops']} | Route: {r['route_str']} | Airlines: {r['airlines']}")

    optimal = find_optimal_route(routes)
    print(f"\nOptimal Route:")
    print(f"{optimal['origin']} → {optimal['destination']} | Airlines: {optimal['airlines']} | Stops: {optimal['stops']} | Total: ${optimal['price']} (Base: ${optimal['base']} + Taxes: ${optimal['taxes']})")
    print(f"Route: {optimal['route_str']}")

    miles_required = None
    for airline in optimal["airlines"]:
        miles_required = get_miles_required(optimal["origin"], optimal["destination"], airline)
        if miles_required:
            vpm = calculate_vpm(optimal["price"], optimal["taxes"], miles_required)
            print(f"\nValue per Mile (VPM): ${vpm}/mile | Airline: {allowed_airlines[airline]} | Miles Required: {miles_required}")
            return

    print("\nNo redemption data found for the optimal route. Trying fallback...")

    fallback, fallback_airline, fallback_miles = find_cheapest_with_miles(routes)
    if fallback:
        vpm = calculate_vpm(fallback["price"], fallback["taxes"], fallback_miles)
        print(f"\nFallback Redeemable Route:")
        print(f"{fallback['origin']} → {fallback['destination']} | Airline: {allowed_airlines[fallback_airline]} | Route: {fallback['route_str']}")
        print(f"Total: ${fallback['price']} (Base: ${fallback['base']} + Taxes: ${fallback['taxes']})")
        print(f"Value per Mile (VPM): ${vpm}/mile | Miles Required: {fallback_miles}")
    else:
        print("No redeemable routes found.")

if __name__ == "__main__":
    main()
