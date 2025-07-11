import os
import json
from flask import Flask, render_template_string, request
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

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Flight VPM Tool</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(to right, #e0eafc, #cfdef3);
            margin: 0;
            padding: 40px;
            color: #333;
        }
        h1 {
            text-align: center;
            font-size: 36px;
            margin-bottom: 30px;
        }
        form {
            background: white;
            padding: 30px;
            max-width: 700px;
            margin: auto;
            border-radius: 12px;
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.1);
        }
        label {
            font-weight: bold;
            display: block;
            margin-top: 15px;
        }
        select, input[type="date"], button {
            width: 100%;
            padding: 12px;
            margin-top: 8px;
            border: 1px solid #ccc;
            border-radius: 8px;
            box-sizing: border-box;
            font-size: 16px;
        }
        button {
            background-color: #4a90e2;
            color: white;
            border: none;
            cursor: pointer;
            transition: background 0.3s ease;
        }
        button:hover {
            background-color: #357ABD;
        }
        .box {
            background: white;
            padding: 25px;
            max-width: 800px;
            margin: 30px auto;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }
        h2 {
            border-bottom: 2px solid #eee;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }
        ul {
            padding-left: 25px;
        }
        li {
            padding: 8px 0;
            line-height: 1.6;
        }
        .error {
            color: #b30000;
            background-color: #ffe6e6;
            border-left: 6px solid #cc0000;
            padding: 15px;
            font-weight: bold;
            border-radius: 8px;
        }
        p {
            line-height: 1.6;
            margin: 10px 0;
        }
    </style>
</head>
<body>
    <h1>Flight Layover & VPM Calculator</h1>
    <form method="POST">
        <label>Choose a route:</label>
        <select name="route" required>
            <option value="JFK-HEL">New York (JFK) → Helsinki (HEL)</option>
            <option value="SYD-BKK">Sydney (SYD) → Bangkok (BKK)</option>
            <option value="IST-YYZ">Istanbul (IST) → Toronto (YYZ)</option>
        </select>

        <label>Departure date:</label>
        <input type="date" name="date" required>

        <button type="submit">Submit</button>
    </form>

    {% if error %}
    <div class="box error">{{ error }}</div>
    {% endif %}

    {% if result %}
    <div class="box">
        <h2>Top 5 Cheapest Routes (Economy):</h2>
        <ul>
        {% for r in result['routes'] %}
            <li><strong>{{ r['route_str'] }}</strong> — ${{ r['price'] }} (Base: ${{ r['base'] }} + Taxes: ${{ r['taxes'] }}) — Stops: {{ r['stops'] }}</li>
        {% endfor %}
        </ul>

        <h2>Optimal Route:</h2>
        <p><strong>{{ result['optimal']['route_str'] }}</strong> — ${{ result['optimal']['price'] }} — Stops: {{ result['optimal']['stops'] }}</p>

        {% if result.get('vpm') %}
            <h2>Value Per Mile (VPM):</h2>
            <p><strong>{{ result['vpm']['value'] }}¢/mile</strong> — Airline: {{ result['vpm']['airline'] }} — Miles Required: {{ result['vpm']['miles'] }}</p>
        {% elif result.get('fallback') %}
            <h2>Fallback Route:</h2>
            <p>{{ result['fallback']['route']['route_str'] }} — ${{ result['fallback']['route']['price'] }}</p>
            <p>VPM: {{ result['fallback']['value'] }}¢/mile — {{ result['fallback']['airline'] }} — {{ result['fallback']['miles'] }} miles</p>
        {% else %}
            <p>No redemption data found.</p>
        {% endif %}
    </div>
    {% endif %}
</body>
</html>
"""

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
    key = f"{origin}-{destination}"
    if airline in redemption_chart and key in redemption_chart[airline]:
        return redemption_chart[airline][key]["ECONOMY"]
    return None

def calculate_vpm(price, taxes, miles):
    return round(100 * (price - taxes) / miles, 2)  # cents per mile

def find_optimal_route(routes):
    return sorted(routes, key=lambda r: (r["price"], r["stops"], r["duration"]))[0]

def find_fallback(routes):
    for route in sorted(routes, key=lambda r: r["price"]):
        for airline in route["airlines"]:
            miles = get_miles_required(route["origin"], route["destination"], airline)
            if miles:
                return route, airline, miles
    return None, None, None

@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    error = None

    if request.method == 'POST':
        route = request.form.get('route')
        date = request.form.get('date')
        origin, destination = route.split('-')

        flights = get_flight_data_fixed(origin, destination, date)
        if not flights:
            error = "No flights returned from API."
            return render_template_string(HTML, result=None, error=error)

        routes = parse_flights(flights)
        if not routes:
            error = "No valid flights with allowed airlines."
            return render_template_string(HTML, result=None, error=error)

        top5 = sorted(routes, key=lambda r: r["price"])[:5]
        optimal = find_optimal_route(routes)

        for airline in optimal["airlines"]:
            miles = get_miles_required(optimal["origin"], optimal["destination"], airline)
            if miles:
                result = {
                    "routes": top5,
                    "optimal": optimal,
                    "vpm": {
                        "airline": allowed_airlines[airline],
                        "miles": miles,
                        "value": calculate_vpm(optimal["price"], optimal["taxes"], miles)
                    }
                }
                return render_template_string(HTML, result=result, error=None)

        fallback, fb_airline, fb_miles = find_fallback(routes)
        if fallback:
            result = {
                "routes": top5,
                "optimal": optimal,
                "fallback": {
                    "route": fallback,
                    "airline": allowed_airlines[fb_airline],
                    "miles": fb_miles,
                    "value": calculate_vpm(fallback["price"], fallback["taxes"], fb_miles)
                }
            }
            return render_template_string(HTML, result=result, error=None)

        result = {"routes": top5, "optimal": optimal}
        return render_template_string(HTML, result=result, error=None)

    return render_template_string(HTML, result=None, error=None)

if __name__ == '__main__':
    app.run(debug=True)
