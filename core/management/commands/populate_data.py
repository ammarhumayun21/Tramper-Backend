"""
Management command to populate database with sample locations, airlines, and categories.
This command is idempotent - running it multiple times will not create duplicates.
"""

from django.core.management.base import BaseCommand
from core.models import Location, Airline
from apps.shipments.models import Category


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

    # 50 Categories for Shipment Items
    CATEGORIES_DATA = [
        {"name": "Electronics", "description": "Electronic devices and accessories", "icon": "📱"},
        {"name": "Clothing", "description": "Apparel and fashion items", "icon": "👕"},
        {"name": "Books", "description": "Books, magazines, and printed materials", "icon": "📚"},
        {"name": "Documents", "description": "Official documents and papers", "icon": "📄"},
        {"name": "Cosmetics", "description": "Beauty and personal care products", "icon": "💄"},
        {"name": "Jewelry", "description": "Jewelry and precious accessories", "icon": "💍"},
        {"name": "Toys", "description": "Children's toys and games", "icon": "🧸"},
        {"name": "Food", "description": "Non-perishable food items", "icon": "🍫"},
        {"name": "Medicine", "description": "Medical supplies and pharmaceuticals", "icon": "💊"},
        {"name": "Shoes", "description": "Footwear of all types", "icon": "👟"},
        {"name": "Bags", "description": "Handbags, backpacks, and luggage", "icon": "👜"},
        {"name": "Watches", "description": "Watches and timepieces", "icon": "⌚"},
        {"name": "Glasses", "description": "Eyewear and sunglasses", "icon": "👓"},
        {"name": "Accessories", "description": "Fashion accessories", "icon": "🎀"},
        {"name": "Sports Equipment", "description": "Sports and fitness gear", "icon": "⚽"},
        {"name": "Musical Instruments", "description": "Musical instruments and accessories", "icon": "🎸"},
        {"name": "Art Supplies", "description": "Art and craft materials", "icon": "🎨"},
        {"name": "Home Decor", "description": "Decorative items for home", "icon": "🖼️"},
        {"name": "Kitchen Items", "description": "Kitchen utensils and gadgets", "icon": "🍳"},
        {"name": "Baby Products", "description": "Baby care and nursery items", "icon": "👶"},
        {"name": "Pet Supplies", "description": "Pet food and accessories", "icon": "🐕"},
        {"name": "Office Supplies", "description": "Stationery and office equipment", "icon": "📎"},
        {"name": "Computer Parts", "description": "Computer hardware and components", "icon": "💻"},
        {"name": "Phone Accessories", "description": "Mobile phone cases and accessories", "icon": "📱"},
        {"name": "Camera Equipment", "description": "Cameras and photography gear", "icon": "📷"},
        {"name": "Video Games", "description": "Gaming consoles and video games", "icon": "🎮"},
        {"name": "DVDs & Blu-rays", "description": "Movies and entertainment media", "icon": "📀"},
        {"name": "Musical Albums", "description": "Music CDs and vinyl records", "icon": "💿"},
        {"name": "Tools", "description": "Hardware tools and equipment", "icon": "🔧"},
        {"name": "Garden Supplies", "description": "Gardening tools and seeds", "icon": "🌱"},
        {"name": "Automotive Parts", "description": "Car parts and accessories", "icon": "🚗"},
        {"name": "Bicycle Parts", "description": "Bicycle components and accessories", "icon": "🚴"},
        {"name": "Camping Gear", "description": "Outdoor and camping equipment", "icon": "⛺"},
        {"name": "Fishing Equipment", "description": "Fishing rods and tackle", "icon": "🎣"},
        {"name": "Collectibles", "description": "Collectible items and memorabilia", "icon": "🏆"},
        {"name": "Antiques", "description": "Antique and vintage items", "icon": "🕰️"},
        {"name": "Handicrafts", "description": "Handmade crafts and artisan goods", "icon": "🧵"},
        {"name": "Furniture Parts", "description": "Furniture components and hardware", "icon": "🪑"},
        {"name": "Textiles", "description": "Fabrics and textile materials", "icon": "🧶"},
        {"name": "Electrical Supplies", "description": "Electrical components and wiring", "icon": "🔌"},
        {"name": "Plumbing Supplies", "description": "Plumbing parts and fixtures", "icon": "🚰"},
        {"name": "Paint & Supplies", "description": "Paint and painting supplies", "icon": "🖌️"},
        {"name": "Photography Prints", "description": "Printed photographs and artwork", "icon": "🖼️"},
        {"name": "Souvenirs", "description": "Travel souvenirs and memorabilia", "icon": "🗿"},
        {"name": "Religious Items", "description": "Religious articles and gifts", "icon": "📿"},
        {"name": "Seasonal Items", "description": "Holiday and seasonal decorations", "icon": "🎄"},
        {"name": "Party Supplies", "description": "Party decorations and supplies", "icon": "🎉"},
        {"name": "Educational Materials", "description": "Educational books and materials", "icon": "📖"},
        {"name": "Scientific Equipment", "description": "Scientific instruments and supplies", "icon": "🔬"},
        {"name": "Other", "description": "Miscellaneous items", "icon": "📦"},
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
        
        # Populate categories
        categories_created = 0
        categories_skipped = 0
        
        for category_data in self.CATEGORIES_DATA:
            category, created = Category.objects.get_or_create(
                name=category_data["name"],
                defaults={
                    "description": category_data["description"],
                    "icon": category_data["icon"],
                }
            )
            if created:
                categories_created += 1
                self.stdout.write(f"  Created category: {category}")
            else:
                categories_skipped += 1
                self.stdout.write(f"  Skipped (exists): {category}")
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Categories: {categories_created} created, {categories_skipped} skipped"
            )
        )
        
        self.stdout.write(self.style.SUCCESS("Data population completed!"))
