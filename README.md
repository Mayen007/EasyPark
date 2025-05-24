# Parking Lot Booking System

## Overview

The Parking Lot Booking System is a web application that allows users to book parking slots online. Users can sign up, log in, and reserve slots based on available locations. The system also supports managing bookings.

## Features

- **User Authentication**: Sign up, log in, and manage sessions.
- **Parking Slot Booking**: Select locations, choose check-in and check-out times, and confirm bookings.
- **Pricing Plans**: Choose from Basic, Premium, and VIP tiers.
- **Booking Management**: View, cancel, and manage existing bookings.
- **Admin Panel (Future Feature)**: Manage locations, users, and bookings.

## Installation

### Prerequisites

Ensure you have the following installed:

- Python 3
- Flask
- SQLite (or any preferred database)

### Setup

1. Clone the repository:

   ```sh
   git clone https://github.com/WanjakeKibe/MYSPACE
   cd MYSPACE
   ```

2. Create and activate a virtual environment:

   ```sh
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. Install dependencies:

   ```sh
   pip install -r requirements.txt
   ```

4. Set up the database:

   ```sh
   flask db upgrade  # If using Flask-Migrate
   ```

5. Run the application:
   ```sh
   flask run
   ```
   The app will be available at `http://127.0.0.1:5000/`

## API Endpoints

### Authentication

- `POST /api/signup` - Register a new user.
- `POST /api/login` - Log in a user.
- `POST /api/logout` - Log out the current user.

### Booking

- `POST /api/book` - Create a new booking.
- `GET /api/bookings` - Retrieve user bookings.

## Frontend Implementation

- The frontend is built using **HTML, CSS, and JavaScript**.
- The booking dashboard supports **real-time updates** using AJAX.
- Users can **cancel bookings** via the dashboard.

## Future Enhancements

- **Admin Panel** for managing locations and bookings.
- **Payment Integration** for Premium & VIP bookings.
- **Email Notifications** for booking confirmations.

## License

This project is licensed under the MIT License.
