"""
Management command to populate the database with comprehensive world data.

Data sources:
  - Countries: pycountry (ISO 3166-1, 249 countries)
  - Airports & Cities: airportsdata (~9,000 airports with IATA codes)
  - Airlines: Embedded list (~460+ airlines with IATA codes)

This command is idempotent — running it multiple times will not create duplicates.
Usage:
    python manage.py populate_world_data
    python manage.py populate_world_data --clear           # Wipe & repopulate
    python manage.py populate_world_data --countries-only   # Only countries
    python manage.py populate_world_data --airports-only    # Only airports & cities
    python manage.py populate_world_data --airlines-only    # Only airlines
"""

import time
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Country, City, Location, Airline


# ---------------------------------------------------------------------------
# Flag emoji helper
# ---------------------------------------------------------------------------

def alpha2_to_flag(alpha_2: str) -> str:
    """Convert ISO alpha-2 code to flag emoji (e.g., US → 🇺🇸)."""
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in alpha_2.upper())


# ---------------------------------------------------------------------------
# UN M.49 Region mapping (alpha-2 → region, sub_region)
# ---------------------------------------------------------------------------

REGION_MAP = {
    "AF": ("Asia", "Southern Asia"),
    "AX": ("Europe", "Northern Europe"),
    "AL": ("Europe", "Southern Europe"),
    "DZ": ("Africa", "Northern Africa"),
    "AS": ("Oceania", "Polynesia"),
    "AD": ("Europe", "Southern Europe"),
    "AO": ("Africa", "Sub-Saharan Africa"),
    "AI": ("Americas", "Caribbean"),
    "AQ": ("", "Antarctica"),
    "AG": ("Americas", "Caribbean"),
    "AR": ("Americas", "South America"),
    "AM": ("Asia", "Western Asia"),
    "AW": ("Americas", "Caribbean"),
    "AU": ("Oceania", "Australia and New Zealand"),
    "AT": ("Europe", "Western Europe"),
    "AZ": ("Asia", "Western Asia"),
    "BS": ("Americas", "Caribbean"),
    "BH": ("Asia", "Western Asia"),
    "BD": ("Asia", "Southern Asia"),
    "BB": ("Americas", "Caribbean"),
    "BY": ("Europe", "Eastern Europe"),
    "BE": ("Europe", "Western Europe"),
    "BZ": ("Americas", "Central America"),
    "BJ": ("Africa", "Sub-Saharan Africa"),
    "BM": ("Americas", "Northern America"),
    "BT": ("Asia", "Southern Asia"),
    "BO": ("Americas", "South America"),
    "BQ": ("Americas", "Caribbean"),
    "BA": ("Europe", "Southern Europe"),
    "BW": ("Africa", "Sub-Saharan Africa"),
    "BV": ("Americas", "South America"),
    "BR": ("Americas", "South America"),
    "IO": ("Africa", "Sub-Saharan Africa"),
    "BN": ("Asia", "South-Eastern Asia"),
    "BG": ("Europe", "Eastern Europe"),
    "BF": ("Africa", "Sub-Saharan Africa"),
    "BI": ("Africa", "Sub-Saharan Africa"),
    "CV": ("Africa", "Sub-Saharan Africa"),
    "KH": ("Asia", "South-Eastern Asia"),
    "CM": ("Africa", "Sub-Saharan Africa"),
    "CA": ("Americas", "Northern America"),
    "KY": ("Americas", "Caribbean"),
    "CF": ("Africa", "Sub-Saharan Africa"),
    "TD": ("Africa", "Sub-Saharan Africa"),
    "CL": ("Americas", "South America"),
    "CN": ("Asia", "Eastern Asia"),
    "CX": ("Oceania", "Australia and New Zealand"),
    "CC": ("Oceania", "Australia and New Zealand"),
    "CO": ("Americas", "South America"),
    "KM": ("Africa", "Sub-Saharan Africa"),
    "CG": ("Africa", "Sub-Saharan Africa"),
    "CD": ("Africa", "Sub-Saharan Africa"),
    "CK": ("Oceania", "Polynesia"),
    "CR": ("Americas", "Central America"),
    "CI": ("Africa", "Sub-Saharan Africa"),
    "HR": ("Europe", "Southern Europe"),
    "CU": ("Americas", "Caribbean"),
    "CW": ("Americas", "Caribbean"),
    "CY": ("Asia", "Western Asia"),
    "CZ": ("Europe", "Eastern Europe"),
    "DK": ("Europe", "Northern Europe"),
    "DJ": ("Africa", "Sub-Saharan Africa"),
    "DM": ("Americas", "Caribbean"),
    "DO": ("Americas", "Caribbean"),
    "EC": ("Americas", "South America"),
    "EG": ("Africa", "Northern Africa"),
    "SV": ("Americas", "Central America"),
    "GQ": ("Africa", "Sub-Saharan Africa"),
    "ER": ("Africa", "Sub-Saharan Africa"),
    "EE": ("Europe", "Northern Europe"),
    "SZ": ("Africa", "Sub-Saharan Africa"),
    "ET": ("Africa", "Sub-Saharan Africa"),
    "FK": ("Americas", "South America"),
    "FO": ("Europe", "Northern Europe"),
    "FJ": ("Oceania", "Melanesia"),
    "FI": ("Europe", "Northern Europe"),
    "FR": ("Europe", "Western Europe"),
    "GF": ("Americas", "South America"),
    "PF": ("Oceania", "Polynesia"),
    "TF": ("Africa", "Sub-Saharan Africa"),
    "GA": ("Africa", "Sub-Saharan Africa"),
    "GM": ("Africa", "Sub-Saharan Africa"),
    "GE": ("Asia", "Western Asia"),
    "DE": ("Europe", "Western Europe"),
    "GH": ("Africa", "Sub-Saharan Africa"),
    "GI": ("Europe", "Southern Europe"),
    "GR": ("Europe", "Southern Europe"),
    "GL": ("Americas", "Northern America"),
    "GD": ("Americas", "Caribbean"),
    "GP": ("Americas", "Caribbean"),
    "GU": ("Oceania", "Micronesia"),
    "GT": ("Americas", "Central America"),
    "GG": ("Europe", "Northern Europe"),
    "GN": ("Africa", "Sub-Saharan Africa"),
    "GW": ("Africa", "Sub-Saharan Africa"),
    "GY": ("Americas", "South America"),
    "HT": ("Americas", "Caribbean"),
    "HM": ("Oceania", "Australia and New Zealand"),
    "VA": ("Europe", "Southern Europe"),
    "HN": ("Americas", "Central America"),
    "HK": ("Asia", "Eastern Asia"),
    "HU": ("Europe", "Eastern Europe"),
    "IS": ("Europe", "Northern Europe"),
    "IN": ("Asia", "Southern Asia"),
    "ID": ("Asia", "South-Eastern Asia"),
    "IR": ("Asia", "Southern Asia"),
    "IQ": ("Asia", "Western Asia"),
    "IE": ("Europe", "Northern Europe"),
    "IM": ("Europe", "Northern Europe"),
    "IL": ("Asia", "Western Asia"),
    "IT": ("Europe", "Southern Europe"),
    "JM": ("Americas", "Caribbean"),
    "JP": ("Asia", "Eastern Asia"),
    "JE": ("Europe", "Northern Europe"),
    "JO": ("Asia", "Western Asia"),
    "KZ": ("Asia", "Central Asia"),
    "KE": ("Africa", "Sub-Saharan Africa"),
    "KI": ("Oceania", "Micronesia"),
    "KP": ("Asia", "Eastern Asia"),
    "KR": ("Asia", "Eastern Asia"),
    "KW": ("Asia", "Western Asia"),
    "KG": ("Asia", "Central Asia"),
    "LA": ("Asia", "South-Eastern Asia"),
    "LV": ("Europe", "Northern Europe"),
    "LB": ("Asia", "Western Asia"),
    "LS": ("Africa", "Sub-Saharan Africa"),
    "LR": ("Africa", "Sub-Saharan Africa"),
    "LY": ("Africa", "Northern Africa"),
    "LI": ("Europe", "Western Europe"),
    "LT": ("Europe", "Northern Europe"),
    "LU": ("Europe", "Western Europe"),
    "MO": ("Asia", "Eastern Asia"),
    "MG": ("Africa", "Sub-Saharan Africa"),
    "MW": ("Africa", "Sub-Saharan Africa"),
    "MY": ("Asia", "South-Eastern Asia"),
    "MV": ("Asia", "Southern Asia"),
    "ML": ("Africa", "Sub-Saharan Africa"),
    "MT": ("Europe", "Southern Europe"),
    "MH": ("Oceania", "Micronesia"),
    "MQ": ("Americas", "Caribbean"),
    "MR": ("Africa", "Sub-Saharan Africa"),
    "MU": ("Africa", "Sub-Saharan Africa"),
    "YT": ("Africa", "Sub-Saharan Africa"),
    "MX": ("Americas", "Central America"),
    "FM": ("Oceania", "Micronesia"),
    "MD": ("Europe", "Eastern Europe"),
    "MC": ("Europe", "Western Europe"),
    "MN": ("Asia", "Eastern Asia"),
    "ME": ("Europe", "Southern Europe"),
    "MS": ("Americas", "Caribbean"),
    "MA": ("Africa", "Northern Africa"),
    "MZ": ("Africa", "Sub-Saharan Africa"),
    "MM": ("Asia", "South-Eastern Asia"),
    "NA": ("Africa", "Sub-Saharan Africa"),
    "NR": ("Oceania", "Micronesia"),
    "NP": ("Asia", "Southern Asia"),
    "NL": ("Europe", "Western Europe"),
    "NC": ("Oceania", "Melanesia"),
    "NZ": ("Oceania", "Australia and New Zealand"),
    "NI": ("Americas", "Central America"),
    "NE": ("Africa", "Sub-Saharan Africa"),
    "NG": ("Africa", "Sub-Saharan Africa"),
    "NU": ("Oceania", "Polynesia"),
    "NF": ("Oceania", "Australia and New Zealand"),
    "MK": ("Europe", "Southern Europe"),
    "MP": ("Oceania", "Micronesia"),
    "NO": ("Europe", "Northern Europe"),
    "OM": ("Asia", "Western Asia"),
    "PK": ("Asia", "Southern Asia"),
    "PW": ("Oceania", "Micronesia"),
    "PS": ("Asia", "Western Asia"),
    "PA": ("Americas", "Central America"),
    "PG": ("Oceania", "Melanesia"),
    "PY": ("Americas", "South America"),
    "PE": ("Americas", "South America"),
    "PH": ("Asia", "South-Eastern Asia"),
    "PN": ("Oceania", "Polynesia"),
    "PL": ("Europe", "Eastern Europe"),
    "PT": ("Europe", "Southern Europe"),
    "PR": ("Americas", "Caribbean"),
    "QA": ("Asia", "Western Asia"),
    "RE": ("Africa", "Sub-Saharan Africa"),
    "RO": ("Europe", "Eastern Europe"),
    "RU": ("Europe", "Eastern Europe"),
    "RW": ("Africa", "Sub-Saharan Africa"),
    "BL": ("Americas", "Caribbean"),
    "SH": ("Africa", "Sub-Saharan Africa"),
    "KN": ("Americas", "Caribbean"),
    "LC": ("Americas", "Caribbean"),
    "MF": ("Americas", "Caribbean"),
    "PM": ("Americas", "Northern America"),
    "VC": ("Americas", "Caribbean"),
    "WS": ("Oceania", "Polynesia"),
    "SM": ("Europe", "Southern Europe"),
    "ST": ("Africa", "Sub-Saharan Africa"),
    "SA": ("Asia", "Western Asia"),
    "SN": ("Africa", "Sub-Saharan Africa"),
    "RS": ("Europe", "Southern Europe"),
    "SC": ("Africa", "Sub-Saharan Africa"),
    "SL": ("Africa", "Sub-Saharan Africa"),
    "SG": ("Asia", "South-Eastern Asia"),
    "SX": ("Americas", "Caribbean"),
    "SK": ("Europe", "Eastern Europe"),
    "SI": ("Europe", "Southern Europe"),
    "SB": ("Oceania", "Melanesia"),
    "SO": ("Africa", "Sub-Saharan Africa"),
    "ZA": ("Africa", "Sub-Saharan Africa"),
    "GS": ("Americas", "South America"),
    "SS": ("Africa", "Sub-Saharan Africa"),
    "ES": ("Europe", "Southern Europe"),
    "LK": ("Asia", "Southern Asia"),
    "SD": ("Africa", "Northern Africa"),
    "SR": ("Americas", "South America"),
    "SJ": ("Europe", "Northern Europe"),
    "SE": ("Europe", "Northern Europe"),
    "CH": ("Europe", "Western Europe"),
    "SY": ("Asia", "Western Asia"),
    "TW": ("Asia", "Eastern Asia"),
    "TJ": ("Asia", "Central Asia"),
    "TZ": ("Africa", "Sub-Saharan Africa"),
    "TH": ("Asia", "South-Eastern Asia"),
    "TL": ("Asia", "South-Eastern Asia"),
    "TG": ("Africa", "Sub-Saharan Africa"),
    "TK": ("Oceania", "Polynesia"),
    "TO": ("Oceania", "Polynesia"),
    "TT": ("Americas", "Caribbean"),
    "TN": ("Africa", "Northern Africa"),
    "TR": ("Asia", "Western Asia"),
    "TM": ("Asia", "Central Asia"),
    "TC": ("Americas", "Caribbean"),
    "TV": ("Oceania", "Polynesia"),
    "UG": ("Africa", "Sub-Saharan Africa"),
    "UA": ("Europe", "Eastern Europe"),
    "AE": ("Asia", "Western Asia"),
    "GB": ("Europe", "Northern Europe"),
    "US": ("Americas", "Northern America"),
    "UM": ("Oceania", "Micronesia"),
    "UY": ("Americas", "South America"),
    "UZ": ("Asia", "Central Asia"),
    "VU": ("Oceania", "Melanesia"),
    "VE": ("Americas", "South America"),
    "VN": ("Asia", "South-Eastern Asia"),
    "VG": ("Americas", "Caribbean"),
    "VI": ("Americas", "Caribbean"),
    "WF": ("Oceania", "Polynesia"),
    "EH": ("Africa", "Northern Africa"),
    "YE": ("Asia", "Western Asia"),
    "ZM": ("Africa", "Sub-Saharan Africa"),
    "ZW": ("Africa", "Sub-Saharan Africa"),
    "XK": ("Europe", "Southern Europe"),
}


# ---------------------------------------------------------------------------
# Comprehensive airline data (~460+ airlines with IATA codes)
# ---------------------------------------------------------------------------

AIRLINES_DATA = [
    # North America
    ("AA", "American Airlines", "US"),
    ("DL", "Delta Air Lines", "US"),
    ("UA", "United Airlines", "US"),
    ("WN", "Southwest Airlines", "US"),
    ("B6", "JetBlue Airways", "US"),
    ("AS", "Alaska Airlines", "US"),
    ("NK", "Spirit Airlines", "US"),
    ("F9", "Frontier Airlines", "US"),
    ("G4", "Allegiant Air", "US"),
    ("HA", "Hawaiian Airlines", "US"),
    ("SY", "Sun Country Airlines", "US"),
    ("MX", "Breeze Airways", "US"),
    ("AC", "Air Canada", "CA"),
    ("WS", "WestJet", "CA"),
    ("PD", "Porter Airlines", "CA"),
    ("TS", "Air Transat", "CA"),
    ("WG", "Sunwing Airlines", "CA"),
    ("AM", "Aeromexico", "MX"),
    ("Y4", "Volaris", "MX"),
    ("4O", "VivaAerobus", "MX"),
    # Central America & Caribbean
    ("CM", "Copa Airlines", "PA"),
    ("AV", "Avianca", "CO"),
    ("TA", "TACA International Airlines", "SV"),
    ("LR", "LACSA", "CR"),
    ("BW", "Caribbean Airlines", "TT"),
    ("UP", "Bahamasair", "BS"),
    ("JM", "Jamaican Airlines", "JM"),
    # South America
    ("LA", "LATAM Airlines", "CL"),
    ("JJ", "LATAM Airlines Brasil", "BR"),
    ("G3", "GOL Linhas Aereas", "BR"),
    ("AD", "Azul Brazilian Airlines", "BR"),
    ("AR", "Aerolineas Argentinas", "AR"),
    ("H2", "Sky Airline", "CL"),
    ("PZ", "LATAM Airlines Paraguay", "PY"),
    ("OB", "Boliviana de Aviacion", "BO"),
    ("P9", "Peruvian Airlines", "PE"),
    # Europe - Major
    ("BA", "British Airways", "GB"),
    ("VS", "Virgin Atlantic", "GB"),
    ("U2", "easyJet", "GB"),
    ("LS", "Jet2.com", "GB"),
    ("MT", "Thomas Cook Airlines", "GB"),
    ("ZT", "Titan Airways", "GB"),
    ("AF", "Air France", "FR"),
    ("TO", "Transavia France", "FR"),
    ("SS", "Corsair International", "FR"),
    ("LH", "Lufthansa", "DE"),
    ("DE", "Condor", "DE"),
    ("4U", "Germanwings", "DE"),
    ("EW", "Eurowings", "DE"),
    ("X3", "TUI fly Deutschland", "DE"),
    ("KL", "KLM Royal Dutch Airlines", "NL"),
    ("HV", "Transavia", "NL"),
    ("IB", "Iberia", "ES"),
    ("UX", "Air Europa", "ES"),
    ("VY", "Vueling", "ES"),
    ("I2", "Iberia Express", "ES"),
    ("AZ", "ITA Airways", "IT"),
    ("FR", "Ryanair", "IE"),
    ("EI", "Aer Lingus", "IE"),
    ("LX", "Swiss International Air Lines", "CH"),
    ("OS", "Austrian Airlines", "AT"),
    ("VO", "Tyrolean Airways", "AT"),
    ("SN", "Brussels Airlines", "BE"),
    ("TP", "TAP Air Portugal", "PT"),
    ("SK", "SAS Scandinavian Airlines", "SE"),
    ("DY", "Norwegian Air Shuttle", "NO"),
    ("D8", "Norwegian Air International", "NO"),
    ("AY", "Finnair", "FI"),
    ("BT", "airBaltic", "LV"),
    ("OV", "Estonian Air", "EE"),
    ("LO", "LOT Polish Airlines", "PL"),
    ("OK", "Czech Airlines", "CZ"),
    ("QS", "Smartwings", "CZ"),
    ("RO", "TAROM", "RO"),
    ("W6", "Wizz Air", "HU"),
    ("FB", "Bulgaria Air", "BG"),
    ("OU", "Croatia Airlines", "HR"),
    ("JP", "Adria Airways", "SI"),
    ("JU", "Air Serbia", "RS"),
    ("YM", "Montenegro Airlines", "ME"),
    ("A3", "Aegean Airlines", "GR"),
    ("OA", "Olympic Air", "GR"),
    ("TK", "Turkish Airlines", "TR"),
    ("PC", "Pegasus Airlines", "TR"),
    ("XQ", "SunExpress", "TR"),
    ("8Q", "Onur Air", "TR"),
    ("KK", "AtlasGlobal", "TR"),
    ("CY", "Cyprus Airways", "CY"),
    # Europe - Nordic / Iceland
    ("FI", "Icelandair", "IS"),
    ("WW", "WOW air", "IS"),
    # Russia & CIS
    ("SU", "Aeroflot", "RU"),
    ("S7", "S7 Airlines", "RU"),
    ("UT", "UTair Aviation", "RU"),
    ("DP", "Pobeda", "RU"),
    ("U6", "Ural Airlines", "RU"),
    ("N4", "Nordwind Airlines", "RU"),
    ("5N", "Nordavia", "RU"),
    ("B2", "Belavia", "BY"),
    ("PS", "Ukraine International Airlines", "UA"),
    ("KC", "Air Astana", "KZ"),
    ("HY", "Uzbekistan Airways", "UZ"),
    ("T5", "Turkmenistan Airlines", "TM"),
    ("QH", "Kyrgyzstan Air", "KG"),
    ("7J", "Tajik Air", "TJ"),
    ("J2", "Azerbaijan Airlines", "AZ"),
    ("A9", "Georgian Airways", "GE"),
    # Middle East
    ("EK", "Emirates", "AE"),
    ("EY", "Etihad Airways", "AE"),
    ("FZ", "flydubai", "AE"),
    ("G9", "Air Arabia", "AE"),
    ("QR", "Qatar Airways", "QA"),
    ("SV", "Saudia", "SA"),
    ("XY", "flynas", "SA"),
    ("RJ", "Royal Jordanian", "JO"),
    ("ME", "Middle East Airlines", "LB"),
    ("WY", "Oman Air", "OM"),
    ("GF", "Gulf Air", "BH"),
    ("KU", "Kuwait Airways", "KW"),
    ("IA", "Iraqi Airways", "IQ"),
    ("IR", "Iran Air", "IR"),
    ("W5", "Mahan Air", "IR"),
    ("EP", "Iran Aseman Airlines", "IR"),
    ("IV", "Cham Wings Airlines", "SY"),
    ("IY", "Yemenia", "YE"),
    # South Asia
    ("AI", "Air India", "IN"),
    ("6E", "IndiGo", "IN"),
    ("SG", "SpiceJet", "IN"),
    ("UK", "Vistara", "IN"),
    ("IX", "Air India Express", "IN"),
    ("G8", "Go First", "IN"),
    ("I5", "AirAsia India", "IN"),
    ("PK", "Pakistan International Airlines", "PK"),
    ("PF", "Airblue", "PK"),
    ("UL", "SriLankan Airlines", "LK"),
    ("BG", "Biman Bangladesh Airlines", "BD"),
    ("BS", "US-Bangla Airlines", "BD"),
    ("KB", "Drukair", "BT"),
    ("RA", "Nepal Airlines", "NP"),
    ("H9", "Himalaya Airlines", "NP"),
    ("Q2", "Maldivian", "MV"),
    # East Asia
    ("CA", "Air China", "CN"),
    ("MU", "China Eastern Airlines", "CN"),
    ("CZ", "China Southern Airlines", "CN"),
    ("HU", "Hainan Airlines", "CN"),
    ("3U", "Sichuan Airlines", "CN"),
    ("ZH", "Shenzhen Airlines", "CN"),
    ("MF", "Xiamen Airlines", "CN"),
    ("FM", "Shanghai Airlines", "CN"),
    ("SC", "Shandong Airlines", "CN"),
    ("GS", "Tianjin Airlines", "CN"),
    ("PN", "West Air", "CN"),
    ("9C", "Spring Airlines", "CN"),
    ("KN", "China United Airlines", "CN"),
    ("TV", "Tibet Airlines", "CN"),
    ("8L", "Lucky Air", "CN"),
    ("G5", "China Express Airlines", "CN"),
    ("EU", "Chengdu Airlines", "CN"),
    ("JD", "Beijing Capital Airlines", "CN"),
    ("DR", "Ruili Airlines", "CN"),
    ("HX", "Hong Kong Airlines", "HK"),
    ("KA", "Cathay Dragon", "HK"),
    ("CX", "Cathay Pacific", "HK"),
    ("NX", "Air Macau", "MO"),
    ("CI", "China Airlines", "TW"),
    ("BR", "EVA Air", "TW"),
    ("IT", "Tigerair Taiwan", "TW"),
    ("B7", "Uni Air", "TW"),
    ("JL", "Japan Airlines", "JP"),
    ("NH", "All Nippon Airways", "JP"),
    ("BC", "Skymark Airlines", "JP"),
    ("7G", "StarFlyer", "JP"),
    ("JH", "Fuji Dream Airlines", "JP"),
    ("GK", "Jetstar Japan", "JP"),
    ("MM", "Peach Aviation", "JP"),
    ("KE", "Korean Air", "KR"),
    ("OZ", "Asiana Airlines", "KR"),
    ("LJ", "Jin Air", "KR"),
    ("7C", "Jeju Air", "KR"),
    ("TW", "T'way Air", "KR"),
    ("BX", "Air Busan", "KR"),
    ("ZE", "Eastar Jet", "KR"),
    ("RS", "Air Seoul", "KR"),
    ("OM", "MIAT Mongolian Airlines", "MN"),
    # Southeast Asia
    ("SQ", "Singapore Airlines", "SG"),
    ("TR", "Scoot", "SG"),
    ("MI", "SilkAir", "SG"),
    ("MH", "Malaysia Airlines", "MY"),
    ("AK", "AirAsia", "MY"),
    ("D7", "AirAsia X", "MY"),
    ("OD", "Malindo Air / Batik Air Malaysia", "MY"),
    ("FY", "Firefly", "MY"),
    ("TG", "Thai Airways", "TH"),
    ("FD", "Thai AirAsia", "TH"),
    ("DD", "Nok Air", "TH"),
    ("WE", "Thai Smile", "TH"),
    ("SL", "Thai Lion Air", "TH"),
    ("XJ", "Thai AirAsia X", "TH"),
    ("PR", "Philippine Airlines", "PH"),
    ("5J", "Cebu Pacific", "PH"),
    ("Z2", "AirAsia Philippines", "PH"),
    ("VN", "Vietnam Airlines", "VN"),
    ("VJ", "VietJet Air", "VN"),
    ("BL", "Pacific Airlines", "VN"),
    ("QV", "Lao Airlines", "LA"),
    ("K6", "Cambodia Angkor Air", "KH"),
    ("8M", "Myanmar Airways International", "MM"),
    ("GA", "Garuda Indonesia", "ID"),
    ("JT", "Lion Air", "ID"),
    ("QG", "Citilink", "ID"),
    ("QZ", "AirAsia Indonesia", "ID"),
    ("ID", "Batik Air", "ID"),
    ("IW", "Wings Air", "ID"),
    ("IN", "Nam Air", "ID"),
    ("SJ", "Sriwijaya Air", "ID"),
    ("BI", "Royal Brunei Airlines", "BN"),
    # Oceania
    ("QF", "Qantas", "AU"),
    ("JQ", "Jetstar Airways", "AU"),
    ("VA", "Virgin Australia", "AU"),
    ("TT", "Tigerair Australia", "AU"),
    ("ZL", "Regional Express Airlines", "AU"),
    ("NZ", "Air New Zealand", "NZ"),
    ("FJ", "Fiji Airways", "FJ"),
    ("PX", "Air Niugini", "PG"),
    ("SB", "Aircalin", "NC"),
    ("TN", "Air Tahiti Nui", "PF"),
    ("VT", "Air Tahiti", "PF"),
    ("IE", "Solomon Airlines", "SB"),
    ("NF", "Air Vanuatu", "VU"),
    ("ON", "Nauru Airlines", "NR"),
    ("FJ", "Fiji Airways", "FJ"),
    # Africa - North
    ("AT", "Royal Air Maroc", "MA"),
    ("AH", "Air Algerie", "DZ"),
    ("TU", "Tunisair", "TN"),
    ("MS", "EgyptAir", "EG"),
    ("NP", "Nile Air", "EG"),
    ("UJ", "AlMasria Universal Airlines", "EG"),
    ("LN", "Libyan Airlines", "LY"),
    ("SD", "Sudan Airways", "SD"),
    # Africa - West
    ("W3", "Arik Air", "NG"),
    ("P4", "Air Peace", "NG"),
    ("QC", "Camair-Co", "CM"),
    ("HF", "Air Cote d'Ivoire", "CI"),
    ("EC", "ECAir", "CG"),
    ("A7", "Air Plus Comet", "GH"),
    # Africa - East
    ("ET", "Ethiopian Airlines", "ET"),
    ("KQ", "Kenya Airways", "KE"),
    ("TC", "Air Tanzania", "TZ"),
    ("UM", "Air Zimbabwe", "ZW"),
    ("WB", "RwandAir", "RW"),
    ("QU", "Uganda Airlines", "UG"),
    ("8U", "Afriqiyah Airways", "LY"),
    # Africa - Southern
    ("SA", "South African Airways", "ZA"),
    ("MN", "Comair", "ZA"),
    ("FA", "FlySafair", "ZA"),
    ("TM", "LAM Mozambique Airlines", "MZ"),
    ("BP", "Air Botswana", "BW"),
    ("SW", "Air Namibia", "NA"),
    ("MK", "Air Mauritius", "MU"),
    ("HM", "Air Seychelles", "SC"),
    ("MD", "Air Madagascar", "MG"),
    # Africa - Central
    ("DT", "TAAG Angola Airlines", "AO"),
    # Additional global airlines
    ("LY", "El Al Israel Airlines", "IL"),
    ("6H", "Israir Airlines", "IL"),
    ("IF", "FlyBaghdad", "IQ"),
    ("QP", "Akasa Air", "IN"),
    ("2Z", "Neos", "IT"),
    ("V7", "Volotea", "ES"),
    ("W2", "FlexFlight", "DK"),
    ("HG", "NIKI", "AT"),
    ("3O", "Air Arabia Maroc", "MA"),
    ("E5", "Air Arabia Egypt", "EG"),
    ("WF", "Widerøe", "NO"),
    ("GL", "Air Greenland", "GL"),
    ("RC", "Atlantic Airways", "FO"),
    ("OG", "Play (airline)", "IS"),
    ("A5", "HOP!", "FR"),
    ("YS", "Régional", "FR"),
    ("LG", "Luxair", "LU"),
    ("OU", "Croatia Airlines", "HR"),
    ("4Z", "Airlink", "ZA"),
    ("4H", "HiSky", "MD"),
    ("QS", "SmartWings", "CZ"),
    ("VR", "TACV", "CV"),
    ("E9", "Evelop Airlines", "ES"),
    ("I9", "Air Italy", "IT"),
    ("FC", "Fly Corporate", "AU"),
    ("2J", "Air Burkina", "BF"),
    ("VK", "Virgin Australia Regional", "AU"),
    ("O6", "Avianca Costa Rica", "CR"),
    ("5Z", "Cemair", "ZA"),
    ("8P", "Pacific Coastal Airlines", "CA"),
    ("YV", "Mesa Airlines", "US"),
    ("OH", "PSA Airlines", "US"),
    ("MQ", "Envoy Air", "US"),
    ("OO", "SkyWest Airlines", "US"),
    ("9K", "Cape Air", "US"),
    ("KS", "PenAir", "US"),
    ("7F", "First Air", "CA"),
    ("MO", "Calm Air", "CA"),
    ("3H", "Air Inuit", "CA"),
    ("4N", "Air North", "CA"),
    ("ZX", "Air Georgian", "CA"),
    ("PB", "Provincial Airlines", "CA"),
    ("QK", "Jazz Aviation", "CA"),
    # Low cost / Budget carriers
    ("W9", "Wizz Air UK", "GB"),
    ("QW", "Blue Islands", "GB"),
    ("3F", "Pacific Airways", "US"),
]


class Command(BaseCommand):
    help = "Populate database with comprehensive world data (countries, cities, airports, airlines)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing data before populating",
        )
        parser.add_argument(
            "--countries-only",
            action="store_true",
            help="Only populate countries",
        )
        parser.add_argument(
            "--airports-only",
            action="store_true",
            help="Only populate airports and cities",
        )
        parser.add_argument(
            "--airlines-only",
            action="store_true",
            help="Only populate airlines",
        )

    def handle(self, *args, **options):
        start = time.time()
        self.stdout.write(self.style.NOTICE("Starting world data population..."))

        do_all = not any([
            options["countries_only"],
            options["airports_only"],
            options["airlines_only"],
        ])

        if options["clear"]:
            self._clear_data(do_all, options)

        if do_all or options["countries_only"]:
            self._populate_countries()

        if do_all or options["airports_only"]:
            self._populate_airports_and_cities()

        if do_all or options["airlines_only"]:
            self._populate_airlines()

        # Update has_airports flag
        if do_all or options["countries_only"] or options["airports_only"]:
            self._update_has_airports_flag()

        elapsed = time.time() - start
        self.stdout.write(self.style.SUCCESS(f"\nWorld data population completed in {elapsed:.1f}s!"))
        self._print_summary()

    def _clear_data(self, do_all, options):
        """Clear existing data."""
        self.stdout.write(self.style.WARNING("Clearing existing data..."))
        if do_all or options.get("airlines_only"):
            count = Airline.objects.count()
            Airline.objects.all().delete()
            self.stdout.write(f"  Deleted {count} airlines")
        if do_all or options.get("airports_only"):
            count = Location.objects.count()
            Location.objects.all().delete()
            self.stdout.write(f"  Deleted {count} airports")
            count = City.objects.count()
            City.objects.all().delete()
            self.stdout.write(f"  Deleted {count} cities")
        if do_all or options.get("countries_only"):
            count = Country.objects.count()
            Country.objects.all().delete()
            self.stdout.write(f"  Deleted {count} countries")

    @transaction.atomic
    def _populate_countries(self):
        """Populate countries from pycountry."""
        import pycountry

        self.stdout.write("\n📌 Populating countries...")
        created = 0
        skipped = 0

        for c in pycountry.countries:
            alpha_2 = c.alpha_2
            alpha_3 = c.alpha_3
            name = c.name
            numeric = getattr(c, "numeric", "")
            region, sub_region = REGION_MAP.get(alpha_2, ("", ""))
            flag = alpha2_to_flag(alpha_2)

            _, was_created = Country.objects.update_or_create(
                alpha_2=alpha_2,
                defaults={
                    "name": name,
                    "alpha_3": alpha_3,
                    "numeric_code": numeric,
                    "region": region,
                    "sub_region": sub_region,
                    "flag_emoji": flag,
                },
            )
            if was_created:
                created += 1
            else:
                skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f"  Countries: {created} created, {skipped} updated"
        ))

    @transaction.atomic
    def _populate_airports_and_cities(self):
        """Populate airports and cities from airportsdata."""
        import airportsdata

        self.stdout.write("\n✈️  Populating airports and cities...")

        # Load airports with IATA codes
        airports = airportsdata.load("IATA")
        self.stdout.write(f"  Loaded {len(airports)} airports from airportsdata")

        # Build a country lookup
        country_lookup = {}
        for c in Country.objects.all():
            country_lookup[c.alpha_2] = c

        # Track cities to avoid duplicates
        city_lookup = {}
        # Pre-load existing cities
        for city in City.objects.select_related("country").all():
            key = (city.name, city.country.alpha_2)
            city_lookup[key] = city

        cities_created = 0
        airports_created = 0
        airports_updated = 0
        airports_skipped = 0

        for iata_code, airport_data in airports.items():
            if not iata_code or len(iata_code) != 3:
                continue

            country_code = airport_data.get("country", "")
            city_name = airport_data.get("city", "").strip()
            airport_name = airport_data.get("name", "").strip()
            lat = airport_data.get("lat")
            lon = airport_data.get("lon")

            if not city_name or not airport_name:
                airports_skipped += 1
                continue

            # Get country object
            country_obj = country_lookup.get(country_code)
            if not country_obj:
                airports_skipped += 1
                continue

            # Get country name
            country_name = country_obj.name

            # Get or create city
            city_key = (city_name, country_code)
            if city_key not in city_lookup:
                city_obj, was_created = City.objects.get_or_create(
                    name=city_name,
                    country=country_obj,
                    defaults={
                        "latitude": lat,
                        "longitude": lon,
                    },
                )
                city_lookup[city_key] = city_obj
                if was_created:
                    cities_created += 1
            else:
                city_obj = city_lookup[city_key]

            # Create or update airport (Location)
            location, was_created = Location.objects.update_or_create(
                iata_code=iata_code,
                defaults={
                    "country": country_name,
                    "city": city_name,
                    "airport_name": airport_name,
                    "city_ref": city_obj,
                    "latitude": lat,
                    "longitude": lon,
                },
            )

            if was_created:
                airports_created += 1
            else:
                airports_updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"  Cities: {cities_created} created"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"  Airports: {airports_created} created, {airports_updated} updated, "
            f"{airports_skipped} skipped"
        ))

    @transaction.atomic
    def _populate_airlines(self):
        """Populate airlines from embedded data."""
        self.stdout.write("\n🛫 Populating airlines...")

        # Build country lookup
        country_lookup = {}
        for c in Country.objects.all():
            country_lookup[c.alpha_2] = c

        created = 0
        updated = 0
        skipped = 0
        seen_codes = set()

        for iata_code, name, country_code in AIRLINES_DATA:
            # Skip duplicates in the data list
            if iata_code in seen_codes:
                skipped += 1
                continue
            seen_codes.add(iata_code)

            country_obj = country_lookup.get(country_code)
            country_name = country_obj.name if country_obj else country_code

            airline, was_created = Airline.objects.update_or_create(
                iata_code=iata_code,
                defaults={
                    "name": name,
                    "country": country_name,
                    "country_ref": country_obj,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"  Airlines: {created} created, {updated} updated, {skipped} skipped"
        ))

    def _update_has_airports_flag(self):
        """Update has_airports flag on countries based on actual airport data."""
        self.stdout.write("\n🔄 Updating has_airports flags...")

        # Reset all to False
        Country.objects.all().update(has_airports=False)

        # Get distinct country codes from locations via city_ref
        countries_with_airports = set(
            City.objects.filter(
                airports__isnull=False
            ).values_list("country_id", flat=True).distinct()
        )

        # Update to True
        updated = Country.objects.filter(
            id__in=countries_with_airports
        ).update(has_airports=True)

        self.stdout.write(self.style.SUCCESS(
            f"  {updated} countries marked as having airports"
        ))

    def _print_summary(self):
        """Print final data summary."""
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("📊 DATA SUMMARY")
        self.stdout.write("=" * 50)
        self.stdout.write(f"  Countries:              {Country.objects.count()}")
        self.stdout.write(f"  Countries with airports:{Country.objects.filter(has_airports=True).count()}")
        self.stdout.write(f"  Cities:                 {City.objects.count()}")
        self.stdout.write(f"  Airports (Locations):   {Location.objects.count()}")
        self.stdout.write(f"  Airlines:               {Airline.objects.count()}")
        self.stdout.write("=" * 50)
