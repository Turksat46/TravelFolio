# Für den Webbetrieb wird Flask verwendet, um die API bereitzustellen.
# Einfach `python main.py` ausführen und die Webseite ist unter http://localhost:5000/ erreichbar.
import time
import os
import uuid
import threading
from flask import Flask, request, render_template, jsonify, make_response, session
from fast_flights import FlightData, Passengers, get_flights, search_airport

import firebase_admin
from firebase_admin import auth, credentials, firestore

import datetime

import airportsdata
import re

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')  # Für Session-Management

# Hilfsfunktion zum Bereinigen von Preisen
def clean_price(price_value):
    """
    Konvertiert Preiswerte zu float, entfernt €-Zeichen, Kommas, etc.
    Beispiele: '€1024' -> 1024.0, '1,234.56' -> 1234.56, '1024' -> 1024.0
    """
    if price_value is None:
        return None

    # Falls bereits eine Zahl, direkt zurückgeben
    if isinstance(price_value, (int, float)):
        return float(price_value)

    # String-Verarbeitung
    if isinstance(price_value, str):
        # Entferne Währungssymbole und Leerzeichen
        cleaned = re.sub(r'[€$£¥\s]', '', price_value)
        # Entferne Tausendertrennzeichen (Komma)
        cleaned = cleaned.replace(',', '')
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return None

    return None

print("Lade Flughafendatenbank für Web-API...")
airports_db = airportsdata.load('IATA')
print(f" Datenbank geladen ({len(airports_db)} Einträge)")

# Firebase Admin SDK Initialisierung
db = None
if(os.path.exists("./firebase-key/travel-e75e6-firebase-adminsdk-fbsvc-7ba67c5552.json")):
    print("Firebase-Schlüssel gefunden und wird geladen.")
    cred = credentials.Certificate("./firebase-key/travel-e75e6-firebase-adminsdk-fbsvc-7ba67c5552.json")
    firebase_admin.initialize_app(cred)
    db = firestore.client()

# Falls ein Cookie schon gespeichert ist, soll dieser geladen werden, um den Nutzer angemeldet zu halten
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

def get_user_id():
    """
    Gibt die User-ID zurück (authenticated user oder anonyme Session)
    Erstellt automatisch eine anonyme Session-ID wenn kein User eingeloggt ist
    """
    # Prüfe zuerst ob User eingeloggt ist
    uid = get_authenticated_user()
    if uid:
        return uid, True  # (user_id, is_authenticated)

    # Falls nicht: Verwende/erstelle anonyme Session-ID
    if 'anonymous_id' not in session:
        session['anonymous_id'] = f"anon_{uuid.uuid4().hex[:16]}"
        print(f"📝 Neue anonyme Session erstellt: {session['anonymous_id']}")

    return session['anonymous_id'], False  # (anonymous_id, is_authenticated)

# Preischecker für Preisalarme
def check_price_alerts():
    """
    Background-Thread, der regelmäßig Preisalarme aller User überprüft
    und neue Preise in Firestore speichert
    """
    while True:
        try:
            print("🔔 Preisalarm-Checker läuft...")
            users_ref = db.collection('artifacts').document('travelfolio-3d-001').collection('users').stream()

            for user_doc in users_ref:
                user_id = user_doc.id
                user_ref = db.collection('artifacts').document('travelfolio-3d-001').collection('users').document(user_id)

                # Hole alle Alerts des Users
                alerts = user_ref.collection('alerts').stream()

                for alert_doc in alerts:
                    alert_data = alert_doc.to_dict()
                    dest = alert_data.get('dest')
                    target_price = alert_data.get('targetPrice')
                    last_seen_price = alert_data.get('lastSeenPrice')
                    notified_at = alert_data.get('notifiedAt')

                    if not dest or not target_price:
                        continue

                    # Konvertiere zu float mit Bereinigung
                    target_price = clean_price(target_price)
                    last_seen_price = clean_price(last_seen_price)

                    if target_price is None:
                        print(f"   ⚠️ Ungültiger Zielpreis für {dest}")
                        continue

                    try:
                        # Suche aktuelle Flugpreise für dieses Ziel
                        # Verwende einen Standard-Abflugort (z.B. Frankfurt) oder den letzten bekannten
                        origin = alert_data.get('origin', 'FRA')

                        # Datum: Verwende gespeichertes Datum oder morgen als Fallback
                        saved_date = alert_data.get('date')
                        if saved_date:
                            search_date = saved_date
                            print(f"      → Verwende gespeichertes Datum: {search_date}")
                        else:
                            search_date = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
                            print(f"      → Kein Datum gespeichert, verwende morgen: {search_date}")

                        # Führe Flugsuche durch
                        flight_data = [FlightData(date=search_date, from_airport=origin, to_airport=dest)]
                        passengers = Passengers(adults=1, children=0, infants_in_seat=0, infants_on_lap=0)

                        result = get_flights(
                            flight_data=flight_data,
                            trip="one-way",
                            seat="economy",
                            passengers=passengers,
                            fetch_mode="local"
                        )

                        if result and result.flights and len(result.flights) > 0:
                            # Günstigster Flug
                            cheapest = min(result.flights, key=lambda f: clean_price(f.price) or float('inf'))
                            current_price = clean_price(cheapest.price)

                            if current_price is None:
                                print(f"   ⚠️ Ungültiger Preis von API für {dest}")
                                continue

                            # Aktualisiere lastSeenPrice
                            update_data = {'lastSeenPrice': current_price}

                            # Prüfe, ob Alarm ausgelöst werden soll
                            if current_price <= target_price:
                                # Nur benachrichtigen, wenn noch nicht benachrichtigt wurde
                                # oder der Preis zwischenzeitlich über dem Zielpreis war
                                should_notify = False
                                if not notified_at:
                                    should_notify = True
                                elif last_seen_price is not None and last_seen_price > target_price:
                                    should_notify = True

                                if should_notify:
                                    update_data['notifiedAt'] = datetime.datetime.now().timestamp()
                                    update_data['triggeredPrice'] = current_price
                                    print(f"   ✅ Preisalarm für {user_id}: {dest} @ {current_price}€ (Ziel: {target_price}€)")
                            else:
                                # Preis über Ziel - reset notifiedAt für erneute Benachrichtigung
                                if notified_at and last_seen_price is not None and last_seen_price <= target_price:
                                    update_data['notifiedAt'] = None

                            # Speichere Aktualisierung
                            alert_doc.reference.update(update_data)

                    except Exception as e:
                        print(f"   ⚠️ Fehler bei Preischeck für {dest}: {e}")
                        continue

        except Exception as e:
            print(f"❌ Fehler im Preisalarm-Checker: {e}")

        # Wartezeit zwischen den Prüfungen (z.B. 1 Stunde = 3600 Sekunden)
        print(f"💤 Nächste Preisüberprüfung in 1 Stunde...")
        time.sleep(3600)

# --- Routen ---

# Home-Verzeichnis
@app.route('/')
def index():
    return render_template('travelfolio.html')

# Anmeldung
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

# Abmeldung
@app.route('/logout', methods=['POST'])
def logout():
    response = make_response(jsonify({'status': 'success'}))
    response.set_cookie('session', '', expires=0)
    return response


# --- FIRESTORE API ENDPUNKTE ---
# Daten abrufen, speichern und löschen für Trips und Alerts
@app.route('/api/data', methods=['GET'])
def get_user_data():
    user_id, is_authenticated = get_user_id()

    try:
        # Pfad: artifacts/travelfolio-3d-001/users/{user_id}/trips
        # Bei anonymen Sessions wird auch Firestore verwendet, nur mit anderer ID
        user_ref = db.collection('artifacts').document('travelfolio-3d-001').collection('users').document(user_id)

        trips = {doc.id: doc.to_dict() for doc in user_ref.collection('trips').stream()}
        alerts = [{**doc.to_dict(), 'id': doc.id} for doc in user_ref.collection('alerts').stream()]

        auth_status = 'authenticated' if is_authenticated else 'anonymous'
        print(f"📊 Daten geladen für {auth_status} User: {len(trips)} Trips, {len(alerts)} Alerts")

        return jsonify({'trips': trips, 'alerts': alerts, 'isAuthenticated': is_authenticated})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Reise speichern
@app.route('/api/trips', methods=['POST'])
def save_trip():
    user_id, is_authenticated = get_user_id()

    data = request.json
    trip_id = data.get('id')
    trip_content = data.get('data')

    try:
        doc_ref = db.collection('artifacts').document('travelfolio-3d-001').collection('users').document(
            user_id).collection('trips').document(trip_id)
        doc_ref.set(trip_content)

        auth_status = 'authenticated' if is_authenticated else 'anonymous'
        print(f"💾 Trip gespeichert für {auth_status} User: {trip_id}")

        return jsonify({'status': 'success', 'isAuthenticated': is_authenticated})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Reise löschen
@app.route('/api/trips/<trip_id>', methods=['DELETE'])
def delete_trip(trip_id):
    user_id, is_authenticated = get_user_id()

    try:
        doc_ref = db.collection('artifacts').document('travelfolio-3d-001').collection('users').document(
            user_id).collection('trips').document(trip_id)
        doc_ref.delete()

        auth_status = 'authenticated' if is_authenticated else 'anonymous'
        print(f"🗑️ Trip gelöscht für {auth_status} User: {trip_id}")

        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Preisalarm speichern
@app.route('/api/alerts', methods=['POST'])
def save_alert():
    user_id, is_authenticated = get_user_id()

    data = request.json
    alert_id = str(data.get('id'))
    alert_content = data.get('data')

    try:
        doc_ref = db.collection('artifacts').document('travelfolio-3d-001').collection('users').document(
            user_id).collection('alerts').document(alert_id)
        doc_ref.set(alert_content)

        auth_status = 'authenticated' if is_authenticated else 'anonymous'
        print(f"🔔 Alert gespeichert für {auth_status} User: {alert_id}")

        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Preisalarm löschen
@app.route('/api/alerts/<alert_id>', methods=['DELETE'])
def delete_alert(alert_id):
    user_id, is_authenticated = get_user_id()

    try:
        doc_ref = db.collection('artifacts').document('travelfolio-3d-001').collection('users').document(
            user_id).collection('alerts').document(alert_id)
        doc_ref.delete()

        auth_status = 'authenticated' if is_authenticated else 'anonymous'
        print(f"🗑️ Alert gelöscht für {auth_status} User: {alert_id}")

        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# --- PREISALARM CHECK API ---
@app.route('/api/check_alerts', methods=['POST'])
def check_alerts():
    """Überprüft Preisalarme manuell und gibt Ergebnisse zurück"""
    user_id, is_authenticated = get_user_id()

    try:
        data = request.json
        alerts = data.get('alerts', [])

        results = []
        for alert in alerts:
            dest = alert.get('dest')
            target_price = alert.get('targetPrice')
            origin = alert.get('origin', 'FRA')

            if not dest or not target_price:
                continue

            # Konvertiere zu float mit Bereinigung
            target_price = clean_price(target_price)
            if target_price is None:
                continue

            try:
                # Datum: Verwende gespeichertes Datum oder morgen als Fallback
                saved_date = alert.get('date')
                if saved_date:
                    search_date = saved_date
                    print(f"      → Verwende gespeichertes Datum: {search_date}")
                else:
                    search_date = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
                    print(f"      → Kein Datum gespeichert, verwende morgen: {search_date}")

                # Flugsuche
                flight_data = [FlightData(date=search_date, from_airport=origin, to_airport=dest)]
                passengers = Passengers(adults=1, children=0, infants_in_seat=0, infants_on_lap=0)

                result = get_flights(
                    flight_data=flight_data,
                    trip="one-way",
                    seat="economy",
                    passengers=passengers,
                    fetch_mode="local"
                )

                if result and result.flights and len(result.flights) > 0:
                    cheapest = min(result.flights, key=lambda f: clean_price(f.price) or float('inf'))
                    current_price = clean_price(cheapest.price)

                    if current_price is not None:
                        results.append({
                            'id': alert.get('id'),
                            'dest': dest,
                            'currentPrice': current_price,
                            'targetPrice': target_price,
                            'triggered': current_price <= target_price
                        })
                        print(f"   ✅ Preis gefunden für {origin} nach {dest}: {current_price}€ (Ziel: {target_price}€)")
                else:
                    print(f"   ⚠️ Keine Flüge gefunden für {dest}")

            except Exception as e:
                print(f"   ❌ Fehler bei Alert-Check für {dest}: {e}")
                continue

        return jsonify({'success': True, 'results': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# --- FLUGSUCHE ---
# Flug suchen
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
    # Starte Preisalarm-Checker-Thread im Hintergrund
    if db:
        price_checker_thread = threading.Thread(target=check_price_alerts, daemon=True)
        price_checker_thread.start()
        print("🔔 Preisalarm-Checker-Thread gestartet")

    app.run(debug=True, port=5000)