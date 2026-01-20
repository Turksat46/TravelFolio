# TravelFolio - Aufgaben

## 📖 Projektbeschreibung

**TravelFolio** ist eine moderne Flight-Search-Anwendung mit interaktivem 3D-Globus. Die App ermöglicht es Nutzern, Flüge über die fast-flights-API zu suchen, Reisen zu planen und auf einer animierten Erdkugel zu visualisieren. Trips werden mit Markern auf dem Globus dargestellt, Flugrouten als leuchtende Bögen gezeichnet, und Preisalarme können gesetzt werden. Die UI kombiniert glassmorphe Design-Elemente mit Three.js-Visualisierungen für ein einzigartiges Nutzererlebnis.

**Tech-Stack**: Flask (Backend), Vanilla JavaScript + Three.js (Frontend), fast-flights-API

---

## 🔴 Kritische Bugs

- [ ] **Flight-Path Arcs bleiben sichtbar**: Alte Routen werden beim neuen Search nicht gelöscht
- [ ] **Keine Fehleranzeige**: API-Fehler werden dem User nicht angezeigt
- [ ] **Date-Input ohne Validation**: Vergangene Daten können eingegeben werden
- [ ] **Passenger Counter Bug**: Kann bei schnellem Klicken negativ werden
- [ ] **Doppelte Trips**: Mehrfaches Klicken auf "Planen" erstellt mehrere identische Trips

## 🟡 Wichtige Features

### Flight Search
- [ ] **Rückflug hinzufügen**: One-way vs. Round-trip Option
- [ ] **Filter-Optionen**:
  - [ ] Max. Anzahl Stops
  - [ ] Abflugzeit-Range
  - [ ] Max. Preis
- [ ] **Sortierung** nach Preis, Dauer, Abflugzeit
- [ ] **Mehr IATA-Codes** in cityDatabase hinzufügen (aktuell nur 7)
- [ ] **Loading States** für Search-Button und Results

### Preisalarme
- [ ] **Alarm-Verwaltung** in der UI (Alarm löschen)
- [ ] **Preis-Tracking visualisieren** (Chart mit Preisverlauf)
- [ ] **Alarm-Details** erweitern (Datum, Route-Info)

### Trip-Management
- [ ] **Trips bearbeiten** (Titel, Datum ändern)
- [ ] **Trip-Notizen** hinzufügen
- [ ] **Trip-Export** als PDF oder JSON
- [ ] **Mehr Itinerary-Items** hinzufügen können

### Globe Visualisierung
- [ ] **Animierte Flugzeuge** entlang der Route
- [ ] **Marker-Tooltips** bei Hover (Stadt-Name, Trip-Info)
- [ ] **Unterschiedliche Marker-Farben** für verschiedene Trip-Status
- [ ] **Click auf Route** zeigt Trip-Details

## 🟢 UX Verbesserungen

- [ ] **Toast-Notifications** für Erfolgs-/Fehlermeldungen
- [ ] **Skeleton Screens** während API-Calls
- [ ] **Mobile Responsiveness** optimieren
- [ ] **Keyboard-Shortcuts** (ESC für Modal schließen)
- [ ] **Smooth Scroll** in Result-Lists
- [ ] **Empty States** mit hilfreichen Texten
- [ ] **Bestätigungs-Dialog** vor Trip-Löschung
- [ ] **Search History** (letzte 5 Suchen)
- [ ] **IATA-Code Autocomplete** mit Dropdown

## 📊 Dashboard

- [ ] **Statistik-Cards erweitern**:
  - [ ] Nächste Reise
  - [ ] Geflogene Kilometer (geschätzt)
  - [ ] Aktive Preisalarme
- [ ] **Reise-Timeline** (chronologische Liste)
- [ ] **Quick-Actions** im Home-View

## 🎨 Visual Polish

- [ ] **Airline-Logos** statt Initialen anzeigen
- [ ] **Bessere Placeholder-Bilder** für Städte (Unsplash API)
- [ ] **Flug-Icons** in Results (Direktflug vs. Stops)
- [ ] **Preis-Trend-Icons** (↑↓) bei Alerts
- [ ] **Smoother Globe-Rotation** bei flyTo()
- [ ] **Glow-Effekt** für ausgewählten Marker

## 🔧 Code-Qualität

- [ ] **Input-Validierung** für alle Formulare
- [ ] **Konstanten auslagern** (API-URL, Farben, etc.)
- [ ] **Funktionen modularisieren** (zu lange Funktionen aufteilen)
- [ ] **Error-Boundaries** für Three.js
- [ ] **Console-Logs entfernen** (nur bei Errors)

---

**Priorität**: Erst 🔴 Bugs fixen, dann 🟡 Features, dann 🟢 UX
