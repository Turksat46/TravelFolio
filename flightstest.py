from fast_flights import FlightData, Passengers, Result, get_flights
import random
from datetime import datetime, timedelta

print("Script gestartet...")

def search_random_flight():
    # Liste einiger großer Flughäfen
    airports = [
        "JFK", # New York
        "LHR", # London Heathrow
        "CDG", # Paris Charles de Gaulle
        "FRA", # Frankfurt
        "DXB", # Dubai
        "HND", # Tokyo Haneda
        "SYD", # Sydney
        "LAX", # Los Angeles
        "SIN", # Singapore
        "AMS"  # Amsterdam
    ]

    # Zufällige Auswahl von Start und Ziel (dürfen nicht gleich sein)
    origin = random.choice(airports)
    destination = random.choice(airports)
    while destination == origin:
        destination = random.choice(airports)

    # Zufälliges Datum in der Zukunft (zwischen 7 und 60 Tagen)
    days_in_future = random.randint(7, 60)
    flight_date = (datetime.now() + timedelta(days=days_in_future)).strftime('%Y-%m-%d')

    print(f"Suche Flug von {origin} nach {destination} am {flight_date}...")

    try:
        # Passagiere konfigurieren (Standard: 1 Erwachsener)
        passengers = Passengers(
            adults=1,
            children=0,
            infants_in_seat=0,
            infants_on_lap=0
        )

        # Flugdaten erstellen
        flight_data_list = [FlightData(
            date=flight_date,
            from_airport=origin,
            to_airport=destination
        )]

        # Suche ausführen
        # mode="flight" wird oft als Standard angenommen, trip="one-way"
        result: Result = get_flights(
            flight_data=flight_data_list,
            trip="one-way",
            seat="economy",
            passengers=passengers,
            fetch_mode="local"
        )

        print("\n--- Suchergebnis ---")
        if result and result.flights:
            print(f"Gefundene Flüge: {len(result.flights)}")
            # Zeige die ersten 3 Flüge
            for i, flight in enumerate(result.flights[:3]):
                print(f"\nFlug {i+1}:")
                print(f"  Airline: {flight.name}") # Manchmal wird 'name' oder 'is_it_airline' verwendet, je nach Version
                print(f"  Preis: {flight.price}")
                print(f"  Abflug: {flight.departure}")
                print(f"  Ankunft: {flight.arrival}")
                print(f"  Dauer: {flight.duration}")
        else:
            print("Keine Flüge gefunden oder Fehler bei der Suche.")

    except Exception as e:
        print(f"Ein Fehler ist aufgetreten: {e}")

if __name__ == "__main__":
    search_random_flight()
