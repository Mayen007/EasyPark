// Fetch parking locations from API
let parkingLocations = [];

async function fetchParkingSpots() {
  try {
    const response = await fetch('/api/parking-spots');
    if (!response.ok) {
      throw new Error('Failed to fetch parking spots');
    }
    parkingLocations = await response.json();
    populateLocationDropdown();
  } catch (error) {
    console.error('Error fetching parking locations:', error);
    alert('Failed to load parking locations. Please refresh the page.');
  }
}

function populateLocationDropdown() {
  const locationSelect = document.getElementById("location");
  if (!locationSelect) return;

  // Clear existing options except the first one (placeholder)
  locationSelect.innerHTML = '<option disabled selected value>Select Location</option>';

  parkingLocations.forEach(parking => {
    let option = document.createElement("option");
    option.value = parking.id;
    option.textContent = `${parking.name} - ${parking.location}`;

    // Add availability info if available
    if (parking.available_slots !== undefined) {
      option.textContent += ` (${parking.available_slots} slots)`;
    }

    // Store additional data as data attributes for easy access
    option.dataset.hourlyRate = parking.hourly_rate;
    option.dataset.dailyRate = parking.daily_rate;
    option.dataset.availableSlots = parking.available_slots || parking.total_slots;

    locationSelect.appendChild(option);
  });
}

// Load parking locations when page loads
document.addEventListener('DOMContentLoaded', function () {
  fetchParkingSpots();
});

const bookNowBtn = document.querySelector(".book-now");
const form = document.querySelector("form");

if (form) {
  form.addEventListener("submit", function (event) {
    event.preventDefault();
    const locationId = document.getElementById("location").value;
    const selectedLocation = parkingLocations.find(parking => parking.id == locationId);
    const locationName = selectedLocation ? selectedLocation.name : 'Unknown Location';
    const checkInDate = document.getElementById("check-in-date").value;
    const checkInTime = document.getElementById("check-in-time").value;
    const checkOutDate = document.getElementById("check-out-date").value;
    const checkOutTime = document.getElementById("check-out-time").value;
    const promoCode = document.getElementById("promo-code").value;

    if (!locationId || !checkInDate || !checkInTime || !checkOutDate || !checkOutTime) {
      alert("Please fill in all required fields.");
      return;
    }

    // Show spinner and disable the button while processing
    const bookButton = document.getElementById("book-button");
    const spinner = document.getElementById("spinner");
    const buttonText = document.getElementById("button-text");
    bookButton.disabled = true;
    spinner.classList.remove("d-none");
    buttonText.textContent = "Processing...";

    const bookingData = {
      location_id: parseInt(locationId, 10),
      check_in_date: checkInDate,
      check_in_time: checkInTime,
      check_out_date: checkOutDate,
      check_out_time: checkOutTime,
      promo_code: promoCode
    };

    // Send booking data to the backend API
    fetch("/api/book", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(bookingData)
    })
      .then(response => response.json())
      .then(data => {
        console.log("Booking successful:", data);

        // Update modal content with the booking details
        document.getElementById("modal-location").textContent = locationName;
        document.getElementById("modal-checkin").textContent = `${checkInDate} ${checkInTime}`;
        document.getElementById("modal-checkout").textContent = `${checkOutDate} ${checkOutTime}`;
        document.getElementById("modal-promo").textContent = promoCode;
        document.getElementById("modal-reference").textContent = data.booking_reference;
        document.getElementById("modal-price").textContent = `KES ${data.total_price.toFixed(2)}`;

        // Show the Bootstrap modal
        let bookingModal = new bootstrap.Modal(document.getElementById("bookingModal"));
        bookingModal.show();
      })
      .catch(error => {
        console.error("Error booking parking:", error);
      })
      .finally(() => {
        // Hide spinner and re-enable the button regardless of outcome
        bookButton.disabled = false;
        spinner.classList.add("d-none");
        buttonText.textContent = "Book Now";
      });
  });
}

// Signup form handler (only if form exists)
const signupForm = document.getElementById("signupForm");
if (signupForm) {
  signupForm.addEventListener("submit", function (e) {
    e.preventDefault();
    fetch("/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: document.getElementById("username").value,
        email: document.getElementById("email").value,
        password: document.getElementById("password").value
      })
    })
      .then(res => res.json())
      .then(data => alert(data.message))
      .catch(err => console.error(err));
  });
}

let inactivityTime = 10 * 60 * 1000; // 10 minutes
let timeout;

function resetTimer() {
  clearTimeout(timeout);
  timeout = setTimeout(() => {
    fetch("{{ url_for('main.logout') }}")
      .then(() => window.location.href = "{{ url_for('main.login') }}");
  }, inactivityTime);
}

document.addEventListener("mousemove", resetTimer);
document.addEventListener("keydown", resetTimer);
document.addEventListener("click", resetTimer);

resetTimer();