import flask
from flask import Flask, request, render_template, jsonify
from fast_flights import FlightData, Passengers, Result, get_flights


import datetime

app = Flask(__name__)


@app.route('/')
def index():
    # Hauptseite laden
    return render_template('travelfolio.html')


@app.route('/api/search', methods=['POST'])
def search():
    """
    Sucht nach Flügen über die fast-flights Bibliothek.
    Fix: FlightData erwartet Keyword-only-Argumente für date, from_airport und to_airport.
    """
    data = request.get_json()

    origin = str(data.get('origin', '').upper())
    destination = str(data.get('destination', '').upper())
    departure_date = str(data.get('date'))
    pass_data = data.get('passengers', {})

    if not all([origin, destination, departure_date]):
        return jsonify({'error': 'Fehlende Parameter (Origin, Destination oder Date)'}), 400

    try:
        # Passagier-Objekt erstellen
        passengers: Passengers = Passengers(
            adults=int(pass_data.get('adults', 1)),
            children=int(pass_data.get('children', 0)),
            infants_in_seat=int(pass_data.get('infants', 0)),
            infants_on_lap=0
        )

        # FIX: FlightData mit den exakt geforderten Keyword-Arguments instanziieren
        # Laut Fehlermeldung: date, from_airport, to_airport
        flight_data = [FlightData(
            date=departure_date,
            from_airport=origin,
            to_airport=destination
        )]

        print(departure_date)

        # Flüge abrufen
        # 'fetch_mode="local"' nutzen, um Google Consent Probleme zu umgehen (benötigt Playwright)
        result:Result = get_flights(
            flight_data=flight_data,
            trip="one-way",
            seat="economy",
            passengers=passengers,
            fetch_mode="local"
        )
        print(result)

        # Ergebnisse für JSON-Response aufbereiten
        flights_list = []
        if result and result.flights:
            for flight in result.flights:
                flights_list.append({
                    'airline': flight.name, # .name wird in aktueller Version verwendet
                    'price': flight.price,
                    'departure': flight.departure,
                    'arrival': flight.arrival,
                    'duration': flight.duration,
                    'stops': flight.stops,

                })

        return jsonify({
            'success': True,
            'origin': origin,
            'destination': destination,
            'flights': flights_list
        })

    except Exception as e:
        print(f"Search Error: {str(e)}")
        # Rückgabe eines detaillierten Fehlers für das Debugging im Frontend
        return jsonify({
            'success': False,
            'error': f"API Fehler: {str(e)}"
        }), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)