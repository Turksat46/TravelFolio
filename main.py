import flask
from flask import Flask, request, render_template, jsonify, make_response
from fast_flights import FlightData, Passengers, Result, get_flights, search_airport

import firebase_admin
from firebase_admin import auth, credentials


import datetime

app = Flask(__name__)

cred = credentials.Certificate("./firebase-key/travel-e75e6-firebase-adminsdk-fbsvc-7ba67c5552.json")
firebase_admin.initialize_app(cred)


@app.route('/')
def index():
    # Cookie laden
    session_cookie = request.cookies.get('session')
    user = None

    if session_cookie:
        try:
            # Session-Cookie verifizieren
            decoded_claims = auth.verify_session_cookie(session_cookie, check_revoked=True)
            user = auth.get_user(decoded_claims['uid'])
        except Exception as e:
            print(f"Session Cookie Error: {str(e)}")
            user = None

    # Hauptseite laden
    return render_template('travelfolio.html')

@app.route('/login', methods=['POST'])
def login():
    id_token = request.json.get('idToken')
    # Session Cookie Laufzeit: 5 Tage
    expires_in = datetime.timedelta(days=5)
    try:
        # Erstelle das Session Cookie aus dem ID-Token
        session_cookie = auth.create_session_cookie(id_token, expires_in=expires_in)
        response = make_response(jsonify({'status': 'success'}))

        # Cookie setzen (httponly für Sicherheit vor XSS)
        response.set_cookie(
            'session',
            session_cookie,
            max_age=int(expires_in.total_seconds()),
            httponly=True,
            secure=False,  # Auf True setzen, wenn HTTPS verwendet wird (Produktion)
            samesite='Lax'
        )
        return response
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 401


@app.route('/logout', methods=['POST'])
def logout():
    response = make_response(jsonify({'status': 'success'}))
    # Cookie im Browser löschen
    response.set_cookie('session', '', expires=0)
    return response

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

    if(len(origin) != 3 or len(destination) !=3):
        search_airport(origin)[0]



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

        if(len(origin) != 3 or len(destination) != 3):
            origin = search_airport(origin)[0]
            destination = search_airport(destination)[0]

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