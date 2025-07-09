from app import create_app, db
from app.models import ParkingSpot
import random


def populate_parking_spots():
    app = create_app()
    with app.app_context():
        # Clear existing spots first
        ParkingSpot.query.delete()

        # Use the same locations from your script.js
        parking_locations = [
            {"name": "CBD Public Parking", "location": "Kenyatta Avenue"},
            {"name": "City Hall Parking", "location": "City Hall Way"},
            {"name": "Globe Roundabout Parking", "location": "Ngara Road"},
            {"name": "Haile Sellasie Parking Lot",
                "location": "Haile Sellasie Avenue"},
            {"name": "Uhuru Park Parking", "location": "Uhuru Highway"},
            {"name": "Sarit Centre Parking", "location": "Westlands"},
            {"name": "The Junction Mall Parking", "location": "Ngong Road"},
            {"name": "Two Rivers Mall Parking", "location": "Limuru Road"},
            {"name": "Westgate Mall Parking", "location": "Mwanzi Road, Westlands"},
            {"name": "Garden City Mall Parking", "location": "Thika Road"},
            {"name": "JKIA Airport Parking",
                "location": "Jomo Kenyatta International Airport"},
            {"name": "Wilson Airport Parking", "location": "Lang'ata Road"},
            {"name": "SGR Terminus Parking", "location": "Syokimau"},
            {"name": "KICC Parking", "location": "Harambee Avenue"},
            {"name": "Hilton Hotel Parking", "location": "Mama Ngina Street"},
            {"name": "Yaya Centre Parking", "location": "Kilimani"},
            {"name": "Village Market Parking", "location": "Gigiri"},
            {"name": "Lavington Mall Parking", "location": "James Gichuru Road"},
            {"name": "Aga Khan Hospital Parking",
                "location": "3rd Parklands Avenue"},
            {"name": "Nairobi Hospital Parking",
                "location": "Argwings Kodhek Road"},
            {"name": "Kenyatta National Hospital Parking",
                "location": "Hospital Road"}
        ]

        for idx, location in enumerate(parking_locations, 1):
            # Set pricing based on location type
            if "Airport" in location["name"]:
                hourly_rate = 200.0
                daily_rate = 1500.0
                total_slots = random.randint(200, 500)
            elif "Mall" in location["name"] or "Centre" in location["name"]:
                hourly_rate = 150.0
                daily_rate = 1000.0
                total_slots = random.randint(100, 300)
            elif "Hospital" in location["name"]:
                hourly_rate = 100.0
                daily_rate = 600.0
                total_slots = random.randint(50, 150)
            else:
                hourly_rate = 120.0
                daily_rate = 800.0
                total_slots = random.randint(30, 100)

            available_slots = int(total_slots * random.uniform(0.8, 0.95))

            spot = ParkingSpot(
                id=idx,
                name=location["name"],
                location=location["location"],
                total_slots=total_slots,
                available_slots=available_slots,
                hourly_rate=hourly_rate,
                daily_rate=daily_rate,
                security_features="CCTV, Security Guards, Motion Sensors",
                amenities="Covered Parking, EV Charging Points, Mobile App Access"
            )
            db.session.add(spot)

        db.session.commit()
        print(f"✅ Successfully added {len(parking_locations)} parking spots!")


if __name__ == '__main__':
    populate_parking_spots()
