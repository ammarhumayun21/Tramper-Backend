"""
Management command to populate database with sample locations and airlines.
This command is idempotent - running it multiple times will not create duplicates.
"""

from django.core.management.base import BaseCommand
from core.models import Location, Airline


class Command(BaseCommand):
    help = "Populate database with sample locations and airlines"

    # 20 Popular Airport Locations
    LOCATIONS_DATA = [
        {"country": "United States", "city": "New York", "airport_name": "John F. Kennedy International Airport", "iata_code": "JFK"},
        {"country": "United States", "city": "Los Angeles", "airport_name": "Los Angeles International Airport", "iata_code": "LAX"},
        {"country": "United States", "city": "Chicago", "airport_name": "O'Hare International Airport", "iata_code": "ORD"},
        {"country": "United Kingdom", "city": "London", "airport_name": "Heathrow Airport", "iata_code": "LHR"},
        {"country": "United Kingdom", "city": "London", "airport_name": "Gatwick Airport", "iata_code": "LGW"},
        {"country": "France", "city": "Paris", "airport_name": "Charles de Gaulle Airport", "iata_code": "CDG"},
        {"country": "Germany", "city": "Frankfurt", "airport_name": "Frankfurt Airport", "iata_code": "FRA"},
        {"country": "Netherlands", "city": "Amsterdam", "airport_name": "Amsterdam Airport Schiphol", "iata_code": "AMS"},
        {"country": "United Arab Emirates", "city": "Dubai", "airport_name": "Dubai International Airport", "iata_code": "DXB"},
        {"country": "Singapore", "city": "Singapore", "airport_name": "Singapore Changi Airport", "iata_code": "SIN"},
        {"country": "Japan", "city": "Tokyo", "airport_name": "Narita International Airport", "iata_code": "NRT"},
        {"country": "Japan", "city": "Tokyo", "airport_name": "Haneda Airport", "iata_code": "HND"},
        {"country": "South Korea", "city": "Seoul", "airport_name": "Incheon International Airport", "iata_code": "ICN"},
        {"country": "China", "city": "Hong Kong", "airport_name": "Hong Kong International Airport", "iata_code": "HKG"},
        {"country": "Australia", "city": "Sydney", "airport_name": "Sydney Kingsford Smith Airport", "iata_code": "SYD"},
        {"country": "Canada", "city": "Toronto", "airport_name": "Toronto Pearson International Airport", "iata_code": "YYZ"},
        {"country": "Turkey", "city": "Istanbul", "airport_name": "Istanbul Airport", "iata_code": "IST"},
        {"country": "Spain", "city": "Madrid", "airport_name": "Adolfo Suárez Madrid–Barajas Airport", "iata_code": "MAD"},
        {"country": "Qatar", "city": "Doha", "airport_name": "Hamad International Airport", "iata_code": "DOH"},
        {"country": "Thailand", "city": "Bangkok", "airport_name": "Suvarnabhumi Airport", "iata_code": "BKK"},
    ]

    # 30 Major Airlines
    AIRLINES_DATA = [
        {"name": "American Airlines", "iata_code": "AA", "country": "United States", "logo_url": ""},
        {"name": "Delta Air Lines", "iata_code": "DL", "country": "United States", "logo_url": ""},
        {"name": "United Airlines", "iata_code": "UA", "country": "United States", "logo_url": ""},
        {"name": "Southwest Airlines", "iata_code": "WN", "country": "United States", "logo_url": ""},
        {"name": "JetBlue Airways", "iata_code": "B6", "country": "United States", "logo_url": ""},
        {"name": "British Airways", "iata_code": "BA", "country": "United Kingdom", "logo_url": ""},
        {"name": "Virgin Atlantic", "iata_code": "VS", "country": "United Kingdom", "logo_url": ""},
        {"name": "Air France", "iata_code": "AF", "country": "France", "logo_url": ""},
        {"name": "Lufthansa", "iata_code": "LH", "country": "Germany", "logo_url": ""},
        {"name": "KLM Royal Dutch Airlines", "iata_code": "KL", "country": "Netherlands", "logo_url": ""},
        {"name": "Emirates", "iata_code": "EK", "country": "United Arab Emirates", "logo_url": ""},
        {"name": "Etihad Airways", "iata_code": "EY", "country": "United Arab Emirates", "logo_url": ""},
        {"name": "Qatar Airways", "iata_code": "QR", "country": "Qatar", "logo_url": ""},
        {"name": "Singapore Airlines", "iata_code": "SQ", "country": "Singapore", "logo_url": ""},
        {"name": "Cathay Pacific", "iata_code": "CX", "country": "Hong Kong", "logo_url": ""},
        {"name": "Japan Airlines", "iata_code": "JL", "country": "Japan", "logo_url": ""},
        {"name": "All Nippon Airways", "iata_code": "NH", "country": "Japan", "logo_url": ""},
        {"name": "Korean Air", "iata_code": "KE", "country": "South Korea", "logo_url": ""},
        {"name": "Asiana Airlines", "iata_code": "OZ", "country": "South Korea", "logo_url": ""},
        {"name": "Qantas", "iata_code": "QF", "country": "Australia", "logo_url": ""},
        {"name": "Air Canada", "iata_code": "AC", "country": "Canada", "logo_url": ""},
        {"name": "Turkish Airlines", "iata_code": "TK", "country": "Turkey", "logo_url": ""},
        {"name": "Iberia", "iata_code": "IB", "country": "Spain", "logo_url": ""},
        {"name": "Swiss International Air Lines", "iata_code": "LX", "country": "Switzerland", "logo_url": ""},
        {"name": "Austrian Airlines", "iata_code": "OS", "country": "Austria", "logo_url": ""},
        {"name": "Thai Airways", "iata_code": "TG", "country": "Thailand", "logo_url": ""},
        {"name": "Malaysia Airlines", "iata_code": "MH", "country": "Malaysia", "logo_url": ""},
        {"name": "Air New Zealand", "iata_code": "NZ", "country": "New Zealand", "logo_url": ""},
        {"name": "Scandinavian Airlines", "iata_code": "SK", "country": "Sweden", "logo_url": ""},
        {"name": "Finnair", "iata_code": "AY", "country": "Finland", "logo_url": ""},
    ]

    def handle(self, *args, **options):
        self.stdout.write("Starting data population...")
        
        # Populate locations
        locations_created = 0
        locations_skipped = 0
        
        for loc_data in self.LOCATIONS_DATA:
            location, created = Location.objects.get_or_create(
                iata_code=loc_data["iata_code"],
                defaults={
                    "country": loc_data["country"],
                    "city": loc_data["city"],
                    "airport_name": loc_data["airport_name"],
                }
            )
            if created:
                locations_created += 1
                self.stdout.write(f"  Created location: {location}")
            else:
                locations_skipped += 1
                self.stdout.write(f"  Skipped (exists): {location}")
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Locations: {locations_created} created, {locations_skipped} skipped"
            )
        )
        
        # Populate airlines
        airlines_created = 0
        airlines_skipped = 0
        
        for airline_data in self.AIRLINES_DATA:
            airline, created = Airline.objects.get_or_create(
                iata_code=airline_data["iata_code"],
                defaults={
                    "name": airline_data["name"],
                    "country": airline_data["country"],
                    "logo_url": airline_data["logo_url"],
                }
            )
            if created:
                airlines_created += 1
                self.stdout.write(f"  Created airline: {airline}")
            else:
                airlines_skipped += 1
                self.stdout.write(f"  Skipped (exists): {airline}")
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Airlines: {airlines_created} created, {airlines_skipped} skipped"
            )
        )
        
        self.stdout.write(self.style.SUCCESS("Data population completed!"))
