import sys
import os
from PySide6.QtCore import QUrl, Qt, Slot, QObject, Signal, QThread
from PySide6.QtGui import QIcon
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel

# Deine Flug-Bibliothek
from fast_flights import FlightData, Passengers, get_flights


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
            passengers = Passengers(
                adults=int(self.pass_data.get('adults', 1)),
                children=int(self.pass_data.get('children', 0)),
                infants_in_seat=int(self.pass_data.get('infants', 0)),
                infants_on_lap=0
            )

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
        except Exception as e:
            self.finished.emit({'success': False, 'error': str(e)})


# --- BRIDGE ---
# Die Schnittstelle, die vom HTML aus aufgerufen werden kann
class Bridge(QObject):
    resultsReady = Signal(dict)

    @Slot(str, str, str, dict)
    def search_flights(self, origin, destination, date, pass_data):
        # Wir erstellen einen neuen Thread für jede Suche
        self.worker = SearchWorker(origin.upper(), destination.upper(), date, pass_data)
        self.worker.finished.connect(lambda data: self.resultsReady.emit(data))
        self.worker.start()


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

        # WebChannel-Setup
        self.channel = QWebChannel()
        self.bridge = Bridge()
        self.channel.registerObject("backend", self.bridge)
        self.browser.page().setWebChannel(self.channel)

        # Pfad zur HTML Datei
        file_path = os.path.abspath("altercode/travelfolio_desktop.html")
        self.browser.load(QUrl.fromLocalFile(file_path))

        self.setCentralWidget(self.browser)


if __name__ == "__main__":
    # Fix für High-DPI Displays (wird in Qt6 automatisch gehandhabt,
    # aber Umgebungsvariablen helfen bei der Konsistenz)
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    app = QApplication(sys.argv)
    window = TravelFolioApp()
    window.show()
    sys.exit(app.exec())