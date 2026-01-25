import sys
import os
from PySide6.QtCore import QUrl, Qt, Slot, QObject, Signal, QThread
from PySide6.QtGui import QIcon
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel

# Deine Flug-Bibliothek
from fast_flights import FlightData, Passengers, get_flights, search_airport


# --- WORKER THREAD ---
# Erledigt die schwere Arbeit im Hintergrund, damit der Globus sich weiterdreht
class SearchWorker(QThread):
    finished = Signal(dict)

    def __init__(self, origin, destination, date, pass_data):
        super().__init__()
        self.origin = origin
        self.destination = destination
        self.date = date
        self.pass_data = pass_data

    def run(self):
        try:
            print(f"SearchWorker started: {self.origin} -> {self.destination} on {self.date}")
            print(f"Passenger data: {self.pass_data}")

            passengers = Passengers(
                adults=int(self.pass_data.get('adults', 1)),
                children=int(self.pass_data.get('children', 0)),
                infants_in_seat=int(self.pass_data.get('infants', 0)),
                infants_on_lap=0
            )

            # Airport-Codes validieren und konvertieren
            # Wenn bereits 3-stelliger Code, verwenden wir ihn direkt
            if len(self.origin) == 3:
                print(f"Verwende Origin-Code direkt: {self.origin}")
            else:
                print(f"Suche Flughafen für Origin: {self.origin}")
                origin_results = search_airport(self.origin)
                print(f"Gefundene Origin-Flughäfen: {origin_results}")
                if not origin_results:
                    raise ValueError(
                        f"Kein Flughafen gefunden für: {self.origin}\n"
                        f"Bitte verwenden Sie den 3-stelligen IATA-Code.\n"
                        f"Beispiele: FRA (Frankfurt), JFK (New York), LHR (London)"
                    )
                self.origin = origin_results[0].value  # .value um den String aus dem Enum zu holen
                print(f"Verwende Origin-Code: {self.origin}")

            if len(self.destination) == 3:
                print(f"Verwende Destination-Code direkt: {self.destination}")
            else:
                print(f"Suche Flughafen für Destination: {self.destination}")
                dest_results = search_airport(self.destination)
                print(f"Gefundene Destination-Flughäfen: {dest_results}")
                if not dest_results:
                    raise ValueError(
                        f"Kein Flughafen gefunden für: {self.destination}\n"
                        f"Bitte verwenden Sie den 3-stelligen IATA-Code.\n"
                        f"Beispiele: NRT (Tokyo Narita), HND (Tokyo Haneda), CDG (Paris)"
                    )
                self.destination = dest_results[0].value  # .value um den String aus dem Enum zu holen
                print(f"Verwende Destination-Code: {self.destination}")

            flight_data = [FlightData(
                date=self.date,
                from_airport=self.origin,
                to_airport=self.destination
            )]

            # Hier passiert das eigentliche "Rendern" der Flugdaten via Playwright
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

            self.finished.emit({
                'success': True,
                'origin': self.origin,
                'destination': self.destination,
                'flights': flights_list
            })
            print(f"Search completed successfully: {len(flights_list)} flights found")
        except Exception as e:
            print(f"Search error: {str(e)}")
            import traceback
            traceback.print_exc()
            self.finished.emit({
                'success': False,
                'error': str(e),
                'origin': self.origin,
                'destination': self.destination
            })


# --- BRIDGE ---
# Die Schnittstelle, die vom HTML aus aufgerufen werden kann
class Bridge(QObject):
    resultsReady = Signal(dict)
    dataLoaded = Signal(dict)  # Signal to send loaded data to JavaScript

    def __init__(self):
        super().__init__()
        self.data_dir = os.path.join(os.path.expanduser("~"), ".travelfolio")
        self.trips_file = os.path.join(self.data_dir, "trips.json")
        self.alerts_file = os.path.join(self.data_dir, "alerts.json")

        # Create data directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)
        print(f"Data directory: {self.data_dir}")

    @Slot(str, str, str, dict)
    def search_flights(self, origin, destination, date, pass_data):
        print(f"Bridge.search_flights called: {origin} -> {destination}, date: {date}")
        print(f"Passenger data type: {type(pass_data)}, value: {pass_data}")
        # Wir erstellen einen neuen Thread für jede Suche
        self.worker = SearchWorker(origin.upper(), destination.upper(), date, pass_data)
        self.worker.finished.connect(lambda data: self.resultsReady.emit(data))
        self.worker.start()
        print("Worker thread started")

    @Slot(str)
    def save_data(self, data_json):
        """Save both trips and alerts data to local JSON files"""
        try:
            import json
            data = json.loads(data_json)

            # Save trips
            if 'trips' in data:
                with open(self.trips_file, 'w', encoding='utf-8') as f:
                    json.dump(data['trips'], f, ensure_ascii=False, indent=2)
                print(f"Trips saved: {len(data['trips'])} trips")

            # Save alerts
            if 'alerts' in data:
                with open(self.alerts_file, 'w', encoding='utf-8') as f:
                    json.dump(data['alerts'], f, ensure_ascii=False, indent=2)
                print(f"Alerts saved: {len(data['alerts'])} alerts")

            return True
        except Exception as e:
            print(f"Error saving data: {e}")
            import traceback
            traceback.print_exc()
            return False

    @Slot()
    def load_data(self):
        """Load data from local JSON files and emit via signal"""
        try:
            import json
            trips = {}
            alerts = []

            # Load trips
            if os.path.exists(self.trips_file):
                with open(self.trips_file, 'r', encoding='utf-8') as f:
                    trips = json.load(f)
                print(f"Trips loaded: {len(trips)} trips")

            # Load alerts
            if os.path.exists(self.alerts_file):
                with open(self.alerts_file, 'r', encoding='utf-8') as f:
                    alerts = json.load(f)
                print(f"Alerts loaded: {len(alerts)} alerts")

            # Emit data via signal
            self.dataLoaded.emit({
                'trips': trips,
                'alerts': alerts
            })
            print("Data emitted via dataLoaded signal")

        except Exception as e:
            print(f"Error loading data: {e}")
            import traceback
            traceback.print_exc()
            # Emit empty data on error
            self.dataLoaded.emit({'trips': {}, 'alerts': []})


class TravelFolioApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TravelFolio 3D")
        self.setWindowIcon(QIcon("./static/logo.png"))
        self.resize(1280, 800)

        # WebEngine-Setup
        self.browser = QWebEngineView()

        settings = self.browser.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True)

        # WebChannel-Setup
        self.channel = QWebChannel()
        self.bridge = Bridge()
        self.channel.registerObject("backend", self.bridge)
        self.browser.page().setWebChannel(self.channel)

        # Pfad zur HTML Datei
        file_path = os.path.abspath("templates/travelfolio.html")
        self.browser.load(QUrl.fromLocalFile(file_path))

        self.setCentralWidget(self.browser)


if __name__ == "__main__":
    # Fix für High-DPI Displays (wird in Qt6 automatisch gehandhabt,
    # aber Umgebungsvariablen helfen bei der Konsistenz)
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    os.environ["QTWEBENGINE_REMOTE_DEBUGGING"] = "9222"

    app = QApplication(sys.argv)
    window = TravelFolioApp()
    window.show()
    sys.exit(app.exec())