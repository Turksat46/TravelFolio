import flask
from flask import Flask, request, render_template, jsonify, make_response
from fast_flights import FlightData, Passengers, Result, get_flights, search_airport

import firebase_admin
from firebase_admin import auth, credentials, firestore

import datetime

import airportsdata

app = Flask(__name__)

print("Lade Flughafendatenbank für Web-API...")
airports_db = airportsdata.load('IATA')
print(f" Datenbank geladen ({len(airports_db)} Einträge)")

# Firebase Admin SDK Initialisierung
# Stelle sicher, dass der Pfad zu deinem Key korrekt ist!
cred = credentials.Certificate("./firebase-key/travel-e75e6-firebase-adminsdk-fbsvc-7ba67c5552.json")
firebase_admin.initialize_app(cred)
db = firestore.client()


def get_authenticated_user():
    """Verifiziert das Session-Cookie und gibt die UID zurück"""
    session_cookie = request.cookies.get('session')
    if not session_cookie:
        return None
    try:
        decoded_claims = auth.verify_session_cookie(session_cookie, check_revoked=True)
        return decoded_claims['uid']
    except Exception:
        return None


@app.route('/')
def index():
    return render_template('travelfolio.html')


@app.route('/login', methods=['POST'])
def login():
    id_token = request.json.get('idToken')
    expires_in = datetime.timedelta(days=5)
    try:
        session_cookie = auth.create_session_cookie(id_token, expires_in=expires_in)
        response = make_response(jsonify({'status': 'success'}))
        response.set_cookie(
            'session',
            session_cookie,
            max_age=int(expires_in.total_seconds()),
            httponly=True,
            secure=False,  # Auf True setzen bei HTTPS
            samesite='Lax'
        )
        return response
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 401


@app.route('/logout', methods=['POST'])
def logout():
    response = make_response(jsonify({'status': 'success'}))
    response.set_cookie('session', '', expires=0)
    return response


# --- FIRESTORE API ENDPOINTS ---

@app.route('/api/data', methods=['GET'])
def get_user_data():
    uid = get_authenticated_user()
    if not uid:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        # Pfad: artifacts/travelfolio-3d-001/users/{uid}/trips
        user_ref = db.collection('artifacts').document('travelfolio-3d-001').collection('users').document(uid)

        trips = {doc.id: doc.to_dict() for doc in user_ref.collection('trips').stream()}
        alerts = [{**doc.to_dict(), 'id': doc.id} for doc in user_ref.collection('alerts').stream()]

        return jsonify({'trips': trips, 'alerts': alerts})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/trips', methods=['POST'])
def save_trip():
    uid = get_authenticated_user()
    if not uid:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json
    trip_id = data.get('id')
    trip_content = data.get('data')

    try:
        doc_ref = db.collection('artifacts').document('travelfolio-3d-001').collection('users').document(
            uid).collection('trips').document(trip_id)
        doc_ref.set(trip_content)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/trips/<trip_id>', methods=['DELETE'])
def delete_trip(trip_id):
    uid = get_authenticated_user()
    if not uid:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        doc_ref = db.collection('artifacts').document('travelfolio-3d-001').collection('users').document(
            uid).collection('trips').document(trip_id)
        doc_ref.delete()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/alerts', methods=['POST'])
def save_alert():
    uid = get_authenticated_user()
    if not uid:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json
    alert_id = str(data.get('id'))
    alert_content = data.get('data')

    try:
        doc_ref = db.collection('artifacts').document('travelfolio-3d-001').collection('users').document(
            uid).collection('alerts').document(alert_id)
        doc_ref.set(alert_content)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/alerts/<alert_id>', methods=['DELETE'])
def delete_alert(alert_id):
    uid = get_authenticated_user()
    if not uid:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        doc_ref = db.collection('artifacts').document('travelfolio-3d-001').collection('users').document(
            uid).collection('alerts').document(alert_id)
        doc_ref.delete()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# --- FLIGHT SEARCH ---

@app.route('/api/search', methods=['POST'])
def search():
    data = request.get_json()
    origin = str(data.get('origin', '').upper())
    destination = str(data.get('destination', '').upper())
    departure_date = str(data.get('date'))
    pass_data = data.get('passengers', {})

    if not all([origin, destination, departure_date]):
        return jsonify({'error': 'Fehlende Parameter'}), 400

    try:
        passengers = Passengers(
            adults=int(pass_data.get('adults', 1)),
            children=int(pass_data.get('children', 0)),
            infants_in_seat=int(pass_data.get('infants', 0)),
            infants_on_lap=0
        )

        # IATA Suche falls nötig
        if len(origin) != 3:
            search_res = search_airport(origin)
            if search_res:
                origin = search_res[0].value if hasattr(search_res[0], 'value') else search_res[0]
        if len(destination) != 3:
            search_res = search_airport(destination)
            if search_res:
                destination = search_res[0].value if hasattr(search_res[0], 'value') else search_res[0]

        flight_data = [FlightData(date=departure_date, from_airport=origin, to_airport=destination)]
        result = get_flights(flight_data=flight_data, trip="one-way", seat="economy", passengers=passengers,
                             fetch_mode="local")

        flights_list = []
        if result and result.flights:
            for flight in result.flights:
                flights_list.append({
                    'airline': flight.name,
                    'price': flight.price,
                    'departure': flight.departure,
                    'arrival': flight.arrival,
                    'duration': flight.duration,
                    'stops': flight.stops,
                })

        coords = {}

        if origin in airports_db:
            apt = airports_db[origin]
            coords[origin] = {'lat': apt['lat'], 'lon': apt['lon']}

        if destination in airports_db:
            apt = airports_db[destination]
            coords[destination] = {'lat': apt['lat'], 'lon': apt['lon']}

        print(f" Web-API: Koordinaten gefunden: {list(coords.keys())}")

        return jsonify({'success': True, 'origin': origin, 'destination': destination, 'flights': flights_list, 'coords': coords})
    except Exception as e:
        print(e)
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)