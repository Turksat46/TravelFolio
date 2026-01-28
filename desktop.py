# TravelFolio Desktop Anwendung
# Nutzt PySide6 für die lokale HTML-Oberfläche
# Webserver wird NUR für die Authentifizierung benutzt

import sys
import os
import json
import datetime
import threading
import airportsdata
import re
from http.server import HTTPServer, SimpleHTTPRequestHandler
from PySide6.QtCore import QUrl, QStandardPaths, Slot, QObject, Signal, QThread
from PySide6.QtGui import QIcon
from PySide6.QtWebEngineCore import QWebEngineSettings, QWebEngineProfile
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel

# Firebase Admin SDK
import firebase_admin
from firebase_admin import credentials, firestore

# Deine Flug-Bibliothek
from fast_flights import FlightData, Passengers, get_flights, search_airport

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

# --- Http-Server für die Authentifizierung ---
class TravelFolioHTTPHandler(SimpleHTTPRequestHandler):
    """Einfacher HTTP Handler für lokale Dateien"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.getcwd(), **kwargs)

    def log_message(self, format, *args):
        # Unterdrücke Server-Logs
        pass

def start_simple_http_server(port=5555):
    """Startet einen einfachen HTTP-Server im Hintergrund"""
    server = HTTPServer(('127.0.0.1', port), TravelFolioHTTPHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"🌐 HTTP-Server läuft auf http://127.0.0.1:{port}")
    return server

# --- FIREBASE INITIALISIERUNG ---
cred_path = "./firebase-key/travel-e75e6-firebase-adminsdk-fbsvc-7ba67c5552.json"
if os.path.exists(cred_path):
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
else:
    print(f"WARNUNG: Firebase Key nicht gefunden unter {cred_path}")
    db = None




# --- WORKER THREAD ---
# Das fungiert wie die main mit den Flugsuchen, aber in einem separaten Thread, damit die Seite nicht hängen bleibt

# Preisalarm-Checker für Desktop-App
class PriceAlertChecker(QThread):
    """Background-Thread der regelmäßig Preisalarme überprüft"""
    alertTriggered = Signal(dict)  # Signal wenn ein Alarm ausgelöst wird

    def __init__(self, bridge):
        super().__init__()
        self.bridge = bridge
        self.running = True
        self.check_interval = 3600  # 1 Stunde in Sekunden

    def run(self):
        while self.running:
            try:
                print("🔔 Desktop: Überprüfe Preisalarme...")
                self.check_all_alerts()
            except Exception as e:
                print(f"❌ Fehler im Preisalarm-Checker: {e}")

            # Warte bis zur nächsten Überprüfung
            for _ in range(self.check_interval):
                if not self.running:
                    break
                self.msleep(1000)  # 1 Sekunde

    def check_all_alerts(self):
        """Überprüft alle Alerts des aktuellen Users"""
        if not db or not self.bridge.current_uid:
            return

        try:
            user_ref = db.collection('artifacts').document(self.bridge.app_id).collection(
                'users').document(self.bridge.current_uid)

            alerts = user_ref.collection('alerts').stream()

            for alert_doc in alerts:
                if not self.running:
                    break

                alert_data = alert_doc.to_dict()
                self.check_single_alert(alert_doc, alert_data)

        except Exception as e:
            print(f"Fehler beim Laden der Alerts: {e}")

    def check_single_alert(self, alert_doc, alert_data):
        #def check_single_alert(self, alert_doc, alert_data):
        """Überprüft einen einzelnen Preisalarm"""
        dest = alert_data.get('dest')
        origin_raw = alert_data.get('origin')
        target_price = alert_data.get('targetPrice')
        last_seen_price = alert_data.get('lastSeenPrice')
        notified_at = alert_data.get('notifiedAt')

        # NEU: Das Datum aus dem Alarm holen!
        # Falls kein Datum gespeichert ist, nehmen wir als Fallback 30 Tage in die Zukunft (statt morgen)
        trip_date = alert_data.get('date')
        if not trip_date:
            trip_date = (datetime.datetime.now() + datetime.timedelta(days=30)).strftime('%Y-%m-%d')
            print(f"   ⚠️ Kein Datum im Alarm für {dest}, nutze Fallback: {trip_date}")

        if not dest or not target_price:
            return

        # Konvertiere zu float mit Bereinigung
        target_price = clean_price(target_price)
        last_seen_price = clean_price(last_seen_price)

        if target_price is None:
            print(f"   ⚠️ Ungültiger Zielpreis für {dest}")
            return

        current_origin = origin_raw
        if len(current_origin) != 3:
            try:
                res = search_airport(current_origin)
                if res:
                    # Nimmt den IATA Code aus dem Suchergebnis
                    current_origin = res[0].value if hasattr(res[0], 'value') else res[0]
            except Exception:
                pass  # Fallback auf den Namen, falls Suche fehlschlägt

        # Zielflughafen auflösen (z.B. "Valencia" -> "VLC")
        current_dest = dest
        if len(current_dest) != 3:
            try:
                res = search_airport(current_dest)
                if res:
                    current_dest = res[0].value if hasattr(res[0], 'value') else res[0]
            except Exception:
                pass

        print(f"🔎 CHECK: {current_origin} -> {current_dest} am {trip_date} (Ziel: {target_price}€)")

        try:
            flight_data = [FlightData(date=trip_date, from_airport=current_origin, to_airport=current_dest)]
            passengers = Passengers(adults=1, children=0, infants_in_seat=0, infants_on_lap=0)

            result = get_flights(
                flight_data=flight_data,
                trip="one-way",
                seat="economy",
                passengers=passengers,
                fetch_mode="local"
            )

            if result and result.flights and len(result.flights) > 0:
                # Günstigsten Preis finden
                cheapest = min(result.flights, key=lambda f: clean_price(f.price) or float('inf'))
                current_price = clean_price(cheapest.price)

                if current_price is None:
                    return

                print(f"   💰 Aktueller Preis: {current_price}€")

                # DB Update vorbereiten
                update_data = {'lastSeenPrice': current_price}
                should_notify = False

                # Alarm-Logik prüfen
                if current_price <= target_price:
                    # Wenn noch nie benachrichtigt ODER Preis wieder gefallen ist
                    if not notified_at:
                        should_notify = True
                    elif last_seen_price is not None and last_seen_price > target_price:
                        should_notify = True

                    if should_notify:
                        update_data['notifiedAt'] = datetime.datetime.now().timestamp()
                        update_data['triggeredPrice'] = current_price
                        print(f"   🚨 ALARM AUSGELÖST!")

                        # Signal an UI senden
                        self.alertTriggered.emit({
                            'dest': dest,
                            'currentPrice': current_price,
                            'targetPrice': target_price,
                            'date': trip_date,
                            'id': alert_doc.id,
                            'triggered': True
                        })
                else:
                    # Preis ist wieder gestiegen -> Reset Notification
                    if notified_at and last_seen_price is not None and last_seen_price <= target_price:
                        update_data['notifiedAt'] = None

                # Speichern
                alert_doc.reference.update(update_data)

                # UI Update auch ohne Alarm (damit Preis aktuell bleibt)
                if not should_notify:
                    self.alertTriggered.emit({
                        'dest': dest,
                        'currentPrice': current_price,
                        'targetPrice': target_price,
                        'id': alert_doc.id,
                        'triggered': False
                    })

            else:
                print(f"   ⚠️ Keine Flüge gefunden.")

        except Exception as e:
            print(f"   ⚠️ Fehler bei Preischeck: {e}")

    def stop(self):
        """Stoppt den Checker-Thread"""
        self.running = False


class SearchWorker(QThread):
    finished = Signal(dict)

    def __init__(self, origin, destination, date, pass_data, airports_db):
        super().__init__()
        self.origin = origin
        self.destination = destination
        self.date = date
        self.pass_data = pass_data
        self.airports_db = airports_db

    def run(self):
        try:
            print(f"Suche gestartet: {self.origin} -> {self.destination} am {self.date}")

            passengers = Passengers(
                adults=int(self.pass_data.get('adults', 1)),
                children=int(self.pass_data.get('children', 0)),
                infants_in_seat=int(self.pass_data.get('infants', 0)),
                infants_on_lap=0
            )

            current_origin = self.origin
            if len(current_origin) != 3:
                res = search_airport(current_origin)
                if res:
                    current_origin = res[0].value if hasattr(res[0], 'value') else res[0]

            current_dest = self.destination
            if len(current_dest) != 3:
                res = search_airport(current_dest)
                if res:
                    current_dest = res[0].value if hasattr(res[0], 'value') else res[0]

            flight_data = [FlightData(
                date=self.date,
                from_airport=current_origin,
                to_airport=current_dest
            )]

            result = get_flights(
                flight_data=flight_data,
                trip="one-way",
                seat="economy",
                passengers=passengers,
                fetch_mode="local"
            )

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
            # Flughafen-Koordinaten holen
            coords = {}

            if current_origin in self.airports_db:
                apt = self.airports_db[current_origin]
                coords[current_origin] = {'lat': apt['lat'], 'lon': apt['lon']}

            if current_dest in self.airports_db:
                apt = self.airports_db[current_dest]
                coords[current_dest] = {'lat': apt['lat'], 'lon': apt['lon']}

            print(f" Koordinaten gefunden für: {list(coords.keys())}")

            self.finished.emit({
                'success': True,
                'origin': current_origin,
                'destination': current_dest,
                'flights': flights_list,
                'coords': coords
            })
        except Exception as e:
            print(f"Suche fehlgeschlagen: {str(e)}")
            self.finished.emit({
                'success': False,
                'error': str(e),
                'origin': self.origin,
                'destination': self.destination
            })


# --- BRIDGE ---
# Hier werden alle API-Calls vom Frontend zum Backend gemacht, bloß dass es in PySide6 ist
class Bridge(QObject):
    resultsReady = Signal(dict)
    dataLoaded = Signal(dict)
    alertChecked = Signal(dict)  # Signal für Preisalarm-Updates

    def __init__(self):
        super().__init__()
        self.current_uid = None
        self.app_id = "travelfolio-3d-001"

        #Flugdatenbank
        print("Lade Flughafendatenbank...")
        self.airports = airportsdata.load('IATA')
        print(f" Datenbank geladen ({len(self.airports)} Flughäfen)")

        # Lokaler Datenpfad
        self.data_dir = os.path.join(os.path.expanduser("~"), ".travelfolio")
        os.makedirs(self.data_dir, exist_ok=True)

        # Session-Datei für persistente UID
        self.session_file = os.path.join(self.data_dir, "session.json")

        # Lade gespeicherte Session beim Start
        self._load_saved_session()

        # Preisalarm-Checker initialisieren
        self.price_checker = None
        if db:
            self.price_checker = PriceAlertChecker(self)
            self.price_checker.alertTriggered.connect(self.alertChecked.emit)
            self.price_checker.start()
            print("🔔 Preisalarm-Checker gestartet")

    def _load_saved_session(self):
        """Lädt gespeicherte User-Session aus lokaler Datei"""
        if os.path.exists(self.session_file):
            try:
                with open(self.session_file, 'r') as f:
                    session_data = json.load(f)
                    expires = session_data.get('expires')
                    if expires and datetime.datetime.fromisoformat(expires) > datetime.datetime.now():
                        self.current_uid = session_data.get('uid')
                        print(f"Gespeicherte Session wiederhergestellt: {self.current_uid}")
                        return self.current_uid
                    else:
                        print("Session abgelaufen")
                        os.remove(self.session_file)
            except Exception as e:
                print(f"Fehler beim Laden der Session: {e}")
        return None

    def _save_session(self, uid, days=5):
        """Speichert User-Session lokal (5 Tage Gültigkeit)"""
        expires = datetime.datetime.now() + datetime.timedelta(days=days)
        session_data = {
            'uid': uid,
            'expires': expires.isoformat()
        }
        with open(self.session_file, 'w') as f:
            json.dump(session_data, f)
        print(f"Session gespeichert bis {expires.strftime('%d.%m.%Y %H:%M')}")

    def _clear_session(self):
        """Löscht gespeicherte Session"""
        if os.path.exists(self.session_file):
            os.remove(self.session_file)
            print("Session gelöscht")

    @Slot(result=str)
    def get_saved_uid(self):
        """Gibt die gespeicherte UID zurück (für automatisches Login)"""
        if self.current_uid:
            return self.current_uid
        return ""

    @Slot(str)
    def set_user_auth(self, uid):
        """Wird aufgerufen, wenn der User sich auf der Seite eingeloggt hat"""
        self.current_uid = uid
        self._save_session(uid)
        print(f"User authentifiziert: {uid}")
        self.load_data()

    @Slot()
    def logout_user(self):
        """Logout - löscht gespeicherte Session"""
        self.current_uid = None
        self._clear_session()
        print("👋 User ausgeloggt")

    # ...existing code...

    @Slot(str, str, str, dict)
    def search_flights(self, origin, destination, date, pass_data):
        self.worker = SearchWorker(origin.upper(), destination.upper(), date, pass_data, self.airports)
        self.worker.finished.connect(self.resultsReady.emit)
        self.worker.start()

    @Slot(dict)
    def check_alert_price(self, alert_data):
        """Überprüft einen einzelnen Preisalarm manuell"""
        try:
            dest = alert_data.get('dest')
            target_price = alert_data.get('targetPrice')
            origin = alert_data.get('origin', 'FRA')

            if not dest or not target_price:
                return

            # Konvertiere zu float mit Bereinigung
            target_price = clean_price(target_price)
            if target_price is None:
                return

            # Datum: morgen
            tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')

            # Flugsuche
            flight_data = [FlightData(date=tomorrow, from_airport=origin, to_airport=dest)]
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

                if current_price is None:
                    return

                self.alertChecked.emit({
                    'id': alert_data.get('id'),
                    'dest': dest,
                    'currentPrice': current_price,
                    'targetPrice': target_price,
                    'triggered': current_price <= target_price
                })
        except Exception as e:
            print(f"Fehler beim Alert-Check: {e}")

    # --- FIRESTORE OPERATIONEN (Analog zu main.py) ---

    @Slot()
    def load_data(self):
        """Lädt Daten aus Firestore (oder lokal, falls nicht eingeloggt)"""
        # Wenn keine UID, versuche gespeicherte Session zu laden
        if not self.current_uid:
            saved_uid = self._load_saved_session()
            if saved_uid:
                self.current_uid = saved_uid

        if not db or not self.current_uid:
            # Fallback auf lokale JSONs wenn kein Firebase/User
            print("Lade lokale Daten (kein Login)")
            self._load_local_data()
            return

        try:
            user_ref = db.collection('artifacts').document(self.app_id).collection('users').document(self.current_uid)

            trips = {doc.id: doc.to_dict() for doc in user_ref.collection('trips').stream()}

            alerts = []
            for doc in user_ref.collection('alerts').stream():
                alert_data = doc.to_dict()
                alert_data['id'] = doc.id
                alerts.append(alert_data)

            print(f"☁️ Daten aus Firestore geladen für {self.current_uid}: {len(trips)} Trips")
            self.dataLoaded.emit({'trips': trips, 'alerts': alerts})
        except Exception as e:
            print(f"Firestore Load Error: {e}")
            self._load_local_data()

    @Slot(str, dict)
    def save_trip(self, trip_id, trip_data):
        if not db or not self.current_uid:
            return self._save_local_trip(trip_id, trip_data)

        try:
            doc_ref = db.collection('artifacts').document(self.app_id).collection('users').document(
                self.current_uid).collection('trips').document(trip_id)
            doc_ref.set(trip_data)
            return True
        except Exception as e:
            print(f"Firestore Save Trip Error: {e}")
            return False

    @Slot(str)
    def delete_trip(self, trip_id):
        if not db or not self.current_uid:
            return self._delete_local_trip(trip_id)

        try:
            doc_ref = db.collection('artifacts').document(self.app_id).collection('users').document(
                self.current_uid).collection('trips').document(trip_id)
            doc_ref.delete()
            return True
        except Exception as e:
            print(f"Firestore Delete Trip Error: {e}")
            return False

    @Slot(dict)
    def save_alert(self, alert_data):
        if not db or not self.current_uid:
            print("Speichere Alarm lokal (kein Login)")
            alert_id = str(alert_data.get('id', datetime.datetime.now().timestamp()))
            return self._save_local_alert(alert_id, alert_data)

        try:
            alert_id = str(alert_data.get('id', datetime.datetime.now().timestamp()))
            doc_ref = db.collection('artifacts').document(self.app_id).collection('users').document(
                self.current_uid).collection('alerts').document(alert_id)
            doc_ref.set(alert_data)
            return True
        except Exception as e:
            print(f"Firestore Save Alert Error: {e}")
            return False

    @Slot(str)
    def delete_alert(self, alert_id):
        if not db or not self.current_uid:
            return self._delete_local_alert(alert_id)
        try:
            doc_ref = db.collection('artifacts').document(self.app_id).collection('users').document(
                self.current_uid).collection('alerts').document(alert_id)
            doc_ref.delete()
            return True
        except Exception as e:
            print(f"Firestore Delete Alert Error: {e}")
            return False

    # --- INTERNE HILFSMETHODEN FÜR LOKALEN FALLBACK ---

    def _load_local_data(self):
        trips_path = os.path.join(self.data_dir, "trips.json")
        alerts_path = os.path.join(self.data_dir, "alerts.json")
        trips = {}
        alerts = []
        if os.path.exists(trips_path):
            with open(trips_path, 'r') as f: trips = json.load(f)
        if os.path.exists(alerts_path):
            with open(alerts_path, 'r') as f: alerts = json.load(f)
        self.dataLoaded.emit({'trips': trips, 'alerts': alerts})

    def _save_local_trip(self, trip_id, trip_data):
        path = os.path.join(self.data_dir, "trips.json")
        data = {}
        if os.path.exists(path):
            with open(path, 'r') as f: data = json.load(f)
        data[trip_id] = trip_data
        with open(path, 'w') as f: json.dump(data, f, indent=2)
        return True

    def _delete_local_trip(self, trip_id):
        path = os.path.join(self.data_dir, "trips.json")
        if not os.path.exists(path): return False
        with open(path, 'r') as f:
            data = json.load(f)
        if trip_id in data:
            del data[trip_id]
            with open(path, 'w') as f: json.dump(data, f, indent=2)
        return True

    def _save_local_alert(self, alert_id, alert_data):
        path = os.path.join(self.data_dir, "alerts.json")
        data = []
        if os.path.exists(path):
            with open(path, 'r') as f: data = json.load(f)
        # Füge neuen Alert hinzu oder aktualisiere bestehenden
        existing_index = next((i for i, a in enumerate(data) if a.get('id') == alert_id), None)
        if existing_index is not None:
            data[existing_index] = alert_data
        else:
            data.append(alert_data)
        with open(path, 'w') as f: json.dump(data, f, indent=2)
        return True

    def _delete_local_alert(self, alert_id):
        path = os.path.join(self.data_dir, "alerts.json")
        if not os.path.exists(path): return False
        with open(path, 'r') as f:
            data = json.load(f)
        # Filtere den Alert heraus
        data = [a for a in data if a.get('id') != alert_id]
        with open(path, 'w') as f: json.dump(data, f, indent=2)
        return True


class PopupWindow(QMainWindow):
    """Separates Fenster für Login-Popups (z.B. Google Auth)"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("TravelFolio - Login")
        self.resize(500, 600)

        self.browser = QWebEngineView()
        settings = self.browser.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True)

        # Debugging
        self.browser.loadStarted.connect(lambda: print(f"🔓 Popup lädt URL..."))
        self.browser.loadFinished.connect(lambda ok: print(f"🔓 Popup geladen: {'✅' if ok else '❌'}"))

        self.setCentralWidget(self.browser)


class TravelFolioApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TravelFolio")
        self.setWindowIcon(QIcon("./static/logo.png"))
        self.resize(1280, 800)

        # Persistentes Profil für Cookie-Speicherung
        profile = QWebEngineProfile.defaultProfile()
        profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)

        # Setze persistenten Storage-Pfad
        storage_path = os.path.join(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation), "TravelFolio")
        os.makedirs(storage_path, exist_ok=True)
        profile.setPersistentStoragePath(storage_path)
        profile.setCachePath(storage_path)

        print(f"Cookie-Speicher: {storage_path}")

        self.browser = QWebEngineView()

        settings = self.browser.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)

        # JavaScript Console Nachrichten im Terminal anzeigen
        self.browser.page().javaScriptConsoleMessage = self.on_console_message

        # Handler für Popup-Fenster (z.B. Google Login)
        self.browser.page().newWindowRequested.connect(self.on_new_window)

        self.channel = QWebChannel()
        self.bridge = Bridge()
        self.channel.registerObject("backend", self.bridge)
        self.browser.page().setWebChannel(self.channel)

        # Lade von lokalem HTTP-Server (für Firebase Auth)
        self.browser.load(QUrl("http://127.0.0.1:5555/templates/travelfolio.html"))
        print(f"Lade: http://127.0.0.1:5555/templates/travelfolio.html")

        self.setCentralWidget(self.browser)

        # Liste der offenen Popup-Fenster
        self.popup_windows = []

    def on_console_message(self, level, message, line, source):
        """Zeigt JavaScript Console Nachrichten im Terminal an"""
        print(f"js: {message}")

    def on_new_window(self, request):
        """Wird aufgerufen, wenn JavaScript window.open() oder ein Popup öffnen möchte"""
        print(f"   Popup-Request erhalten!")
        print(f"   URL: {request.requestedUrl()}")
        print(f"   Destination: {request.destination()}")

        popup = PopupWindow(self)

        # Verbinde das neue Fenster mit der Request
        request.openIn(popup.browser.page())

        # Zeige das Popup-Fenster
        popup.show()

        # Speichere Referenz, damit es nicht garbage collected wird
        self.popup_windows.append(popup)

        # Cleanup wenn Fenster geschlossen wird
        popup.destroyed.connect(lambda: self.popup_windows.remove(popup) if popup in self.popup_windows else None)

        print("Login-Popup-Fenster erstellt und angezeigt")


if __name__ == "__main__":
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    os.environ["QTWEBENGINE_REMOTE_DEBUGGING"] = "9222"

    print("Starte TravelFolio Desktop...")

    # Starte einfachen HTTP-Server für Firebase Auth
    start_simple_http_server(5555)

    app = QApplication(sys.argv)
    window = TravelFolioApp()
    window.show()

    print("App gestartet")

    sys.exit(app.exec())

