# Dokumentation TravelFolio

## Übersicht

Diese Dokumentation beschreibt die Funktionsweise und Nutzung der TravelFolio App, einer Anwendung zur Verwaltung und Planung von Flugreisen. Die App nutzt die fast-flights-API für Fluginformationen und bietet eine benutzerfreundliche Oberfläche.

## Wie es funktioniert
- Die App verwendet die fast-flights-API, die Google Flights scraped, um genaue Informationen zu Preisen, Flügen und mehr bereitzustellen.
- Die Benutzeroberfläche ist intuitiv gestaltet, sodass Nutzer schnell ihre Reisehistorie und geplante Reisen einsehen können.
- Die App bietet die Möglichkeit, Flugdaten in einem Google-Konto zu speichern, erfordert jedoch eine Authentifizierung über Firebase.
- Die App kann auch ohne Login genutzt werden, wobei Daten lokal gespeichert werden.

## Nutzung der App
1. Klone das Repository und öffne es in Pycharm.
2. Installiere die Abhängigkeiten mit dem Befehl `uv sync`.
3. Starte die App entweder als Web-App oder Desktop-App:
    - Für die Web-App: Wähle "Run 'main.py'" aus dem Dropdown
    - Für die Desktop-App: Wähle "Desktop" aus dem Dropdown
4. (optional) Füge die erforderlichen Firebase-Konfigurationsdateien hinzu, um die Login-Funktion freizuschalten
    - `firebase_config.json` im 'firebase-key'-Ordner
    - `travel-e...2.json` im 'static'-Ordner (bereits vorhanden)

## Funktionsweise der App
- Die App ermöglicht es Nutzern, ihre Flugreisen zu planen und zu verwalten.
- Die App ist als Web- und Desktop-Anwendung verfügbar.
- Gegeben ist eine HTML-Seite, welches die Benutzeroberfläche der App darstellt. (Frontend)
- 
    