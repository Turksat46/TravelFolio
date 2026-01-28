<h1 align="center">
<img src="static/logo.png" alt=""/>
</h1>

<h1 align="center">TravelFolio</h1> 

<div align="center">
<h4>Die ultimative FlugApp für Reisen</h4> 
</div>

### WICHTIG
Dieses Projekt wurde mit PyCharm erstellt (aktuellste Version)         
Einfach PyCharm installieren und mit Project from Version Control klonen

### Wie es funktioniert und welche APIs wir nutzen
- Wir benutzen die fast-flights-API, die Google Flights scraped und uns somit genaue Informationen liefert wie Preise, Flüge etc.
- Die UI ist intuitiv und modern dargestellt, sodass jeder Nutzer schnell sieht, wo er mal war und wo er noch hinmöchte.
- Für die Punkte auf der Erde wird die airportsdata-Bibliothek genutzt, die uns die Koordinaten der Flughäfen liefert
- Die 3D-Globus-Visualisierung wird mit Three.js umgesetzt, welches in der Web-App integriert ist
- Wir nutzen Flask als Backend-Framework, um die API-Calls zu tätigen und die Daten an das Frontend zu senden (für die Web-App)
- Für die Desktop-App nutzen wir PyWebView, um die Web-App in einem nativen Fenster darzustellen

### Wie nutze ich die App?
- Einfach das Repository klonen und in PyCharm öffnen
- Mit dem Befehl ```uv sync``` die Abhängigkeiten installieren
- Mit dem Befehl ```playwright install``` den Playwright-Browser installieren
- Ab hier gibt es zwei Möglichkeiten: (Beides findet man oben neben dem Play-Button)
    1. Man startet die Web-App vom Dropdown-Menü aus (Run 'main.py') und öffnet den Browser
  2. Man startet die Desktop-App mit "Desktop" vom Dropdown und es öffnet sich ein Fenster
- Genießen!

In der App gibt es die Möglichkeit, alle gesuchten und geplanten Flüge in seinem Google-Konto zu speichern.       
Jedoch benötigt dies weitere Schritte:
- Man benötigt zwei Dateien, welches man von mir anfordern kann:
  - firebase_config.json im 'firebase-key'-Ordner, welches im Root vom Projekt liegen muss
  - travel-e...2.json im 'static'-Ordner, welches schon existiert.

Nachdem man diese Dateien hinzugefügt hat, sollte das Login funktionieren.
### DIE APP FUNKTIONIERT AUCH OHNE LOGIN UND SPEICHERT DATEN LOKAL!


### Dokumentation
- Für Fast-Flights findet man die Dokumentation [hier](https://aweirddev.github.io/flights/)
- Für airportsdata findet man die Dokumentation [hier](https://github.com/mborsetti/airportsdata/blob/main/README.rst)

