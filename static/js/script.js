const parkingLocations = [
  { "id": 1, "name": "CBD Public Parking", "location": "Kenyatta Avenue" },
  { "id": 2, "name": "City Hall Parking", "location": "City Hall Way" },
  { "id": 3, "name": "Globe Roundabout Parking", "location": "Ngara Road" },
  { "id": 4, "name": "Haile Sellasie Parking Lot", "location": "Haile Sellasie Avenue" },
  { "id": 5, "name": "Uhuru Park Parking", "location": "Uhuru Highway" },
  { "id": 6, "name": "Sarit Centre Parking", "location": "Westlands" },
  { "id": 7, "name": "The Junction Mall Parking", "location": "Ngong Road" },
  { "id": 8, "name": "Two Rivers Mall Parking", "location": "Limuru Road" },
  { "id": 9, "name": "Westgate Mall Parking", "location": "Mwanzi Road, Westlands" },
  { "id": 10, "name": "Garden City Mall Parking", "location": "Thika Road" },
  { "id": 11, "name": "JKIA Airport Parking", "location": "Jomo Kenyatta International Airport" },
  { "id": 12, "name": "Wilson Airport Parking", "location": "Lang'ata Road" },
  { "id": 13, "name": "SGR Terminus Parking", "location": "Syokimau" },
  { "id": 14, "name": "KICC Parking", "location": "Harambee Avenue" },
  { "id": 15, "name": "Hilton Hotel Parking", "location": "Mama Ngina Street" },
  { "id": 16, "name": "Yaya Centre Parking", "location": "Kilimani" },
  { "id": 17, "name": "Village Market Parking", "location": "Gigiri" },
  { "id": 18, "name": "Lavington Mall Parking", "location": "James Gichuru Road" },
  { "id": 19, "name": "Aga Khan Hospital Parking", "location": "3rd Parklands Avenue" },
  { "id": 20, "name": "Nairobi Hospital Parking", "location": "Argwings Kodhek Road" },
  { "id": 21, "name": "Kenyatta National Hospital Parking", "location": "Hospital Road" }
];

const locationSelect = document.getElementById("location");

parkingLocations.forEach(parking => {
  let option = document.createElement("option");
  option.value = parking.id;
  option.textContent = `${parking.name} - ${parking.location}`;
  locationSelect.appendChild(option);
});

// Add availability checking function
function checkAvailability() {
  const locationId = document.getElementById("location").value;
  const checkInDate = document.getElementById("check-in-date").value;
  const checkInTime = document.getElementById("check-in-time").value;
  const checkOutDate = document.getElementById("check-out-date").value;
  const checkOutTime = document.getElementById("check-out-time").value;

  // Only check if all required fields are filled
  if (!locationId || !checkInDate || !checkInTime || !checkOutDate || !checkOutTime) {
    // Clear availability info if fields are empty
    const availabilityDiv = document.getElementById("availability-info");
    if (availabilityDiv) {
      availabilityDiv.remove();
    }
    return;
  }

  // Show loading state
  showAvailabilityLoading();

  fetch("/api/check-availability", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      location_id: parseInt(locationId),
      check_in_date: checkInDate,
      check_in_time: checkInTime,
      check_out_date: checkOutDate,
      check_out_time: checkOutTime
    })
  })
    .then(response => response.json())
    .then(data => {
      if (data.error) {
        showAvailabilityError(data.error);
      } else {
        showAvailabilityResult(data);
      }
    })
    .catch(error => {
      console.error("Error checking availability:", error);
      showAvailabilityError("Unable to check availability. Please try again.");
    });
}

function showAvailabilityLoading() {
  const availabilityDiv = getOrCreateAvailabilityDiv();
  availabilityDiv.innerHTML = `
    <div class="alert alert-info d-flex align-items-center">
      <div class="spinner-border spinner-border-sm me-2" role="status">
        <span class="visually-hidden">Loading...</span>
      </div>
      Checking availability...
    </div>
  `;
}

function showAvailabilityResult(data) {
  const availabilityDiv = getOrCreateAvailabilityDiv();
  const bookButton = document.getElementById("book-button");

  if (data.is_available) {
    availabilityDiv.innerHTML = `
      <div class="alert alert-success">
        <div class="d-flex justify-content-between align-items-center">
          <div>
            <strong><i class="fas fa-check-circle me-1"></i>Available!</strong>
            <br><small>${data.available_slots} slots available</small>
          </div>
          <div class="text-end">
            <strong>KES ${data.estimated_price}</strong>
            <br><small>Estimated Price</small>
          </div>
        </div>
        <hr class="my-2">
        <div class="row">
          <div class="col-6">
            <small><strong>Hourly:</strong> KES ${data.hourly_rate}</small>
          </div>
          <div class="col-6">
            <small><strong>Daily:</strong> KES ${data.daily_rate}</small>
          </div>
        </div>
      </div>
    `;
    if (bookButton) bookButton.disabled = false;
  } else {
    availabilityDiv.innerHTML = `
      <div class="alert alert-danger">
        <strong><i class="fas fa-times-circle me-1"></i>No slots available</strong>
        <br><small>for the selected time period</small>
      </div>
    `;
    if (bookButton) bookButton.disabled = true;
  }
}

function showAvailabilityError(errorMessage) {
  const availabilityDiv = getOrCreateAvailabilityDiv();
  const bookButton = document.getElementById("book-button");

  availabilityDiv.innerHTML = `
    <div class="alert alert-warning">
      <strong><i class="fas fa-exclamation-triangle me-1"></i>Error</strong>
      <br><small>${errorMessage}</small>
    </div>
  `;
  if (bookButton) bookButton.disabled = true;
}

function getOrCreateAvailabilityDiv() {
  let availabilityDiv = document.getElementById("availability-info");
  if (!availabilityDiv) {
    availabilityDiv = document.createElement("div");
    availabilityDiv.id = "availability-info";
    availabilityDiv.className = "mt-3";

    // Insert after the form row
    const formRow = document.querySelector("form .row");
    if (formRow) {
      formRow.insertAdjacentElement('afterend', availabilityDiv);
    }
  }
  return availabilityDiv;
}

// Add event listeners for real-time availability checking
if (document.getElementById("location")) {
  document.getElementById("location").addEventListener("change", checkAvailability);
}
if (document.getElementById("check-in-date")) {
  document.getElementById("check-in-date").addEventListener("change", checkAvailability);
}
if (document.getElementById("check-in-time")) {
  document.getElementById("check-in-time").addEventListener("change", checkAvailability);
}
if (document.getElementById("check-out-date")) {
  document.getElementById("check-out-date").addEventListener("change", checkAvailability);
}
if (document.getElementById("check-out-time")) {
  document.getElementById("check-out-time").addEventListener("change", checkAvailability);
}

const bookNowBtn = document.querySelector(".book-now");
const form = document.querySelector("form");

form.addEventListener("submit", function (event) {
  event.preventDefault();
  const locationId = document.getElementById("location").value;
  const locationName = parkingLocations.find(parking => parking.id == locationId).name;
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
    .then(response => {
      if (!response.ok) {
        return response.json().then(err => Promise.reject(err));
      }
      return response.json();
    })
    .then(data => {
      console.log("Booking successful:", data);

      // Update modal content with the booking details
      document.getElementById("modal-location").textContent = locationName;
      document.getElementById("modal-checkin").textContent = `${checkInDate} ${checkInTime}`;
      document.getElementById("modal-checkout").textContent = `${checkOutDate} ${checkOutTime}`;
      document.getElementById("modal-promo").textContent = promoCode || "None";

      // Add booking reference and price to modal if elements exist
      const modalReference = document.getElementById("modal-reference");
      const modalPrice = document.getElementById("modal-price");
      if (modalReference) modalReference.textContent = data.booking_reference;
      if (modalPrice) modalPrice.textContent = `KES ${data.total_price}`;

      // Show the Bootstrap modal
      let bookingModal = new bootstrap.Modal(document.getElementById("bookingModal"));
      bookingModal.show();

      // Clear the form and availability info after successful booking
      form.reset();
      const availabilityDiv = document.getElementById("availability-info");
      if (availabilityDiv) availabilityDiv.remove();
    })
    .catch(error => {
      console.error("Error booking parking:", error);
      // Show error message to user
      alert(error.error || "Booking failed. Please try again.");
    })
    .finally(() => {
      // Hide spinner and re-enable the button regardless of outcome
      bookButton.disabled = false;
      spinner.classList.add("d-none");
      buttonText.textContent = "Book Now";
    });
});

// ...rest of your existing code...
document.getElementById("signupForm").addEventListener("submit", function (e) {
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

let inactivityTime = 10 * 60 * 1000; // 10 minutes
let timeout;

function resetTimer() {
  clearTimeout(timeout);
  timeout = setTimeout(() => {
    fetch("/logout")
      .then(() => window.location.href = "/login");
  }, inactivityTime);
}

document.addEventListener("mousemove", resetTimer);
document.addEventListener("keydown", resetTimer);
document.addEventListener("click", resetTimer);

resetTimer();