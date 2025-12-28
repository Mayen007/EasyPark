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
    // Get form elements
    const locationElement = document.getElementById("location");
    const checkInDateElement = document.getElementById("check-in-date");
    const checkInTimeElement = document.getElementById("check-in-time");
    const checkOutDateElement = document.getElementById("check-out-date");
    const checkOutTimeElement = document.getElementById("check-out-time");
    const promoCodeElement = document.getElementById("promo-code");

    // Check if booking form elements exist (to avoid errors on other pages)
    if (!locationElement || !checkInDateElement || !checkInTimeElement ||
      !checkOutDateElement || !checkOutTimeElement) {
      return; // Not a booking form, allow normal submission
    }

    // Only prevent default for booking forms
    event.preventDefault();

    const locationId = locationElement.value;
    const selectedLocation = parkingLocations.find(parking => parking.id == locationId);
    const locationName = selectedLocation ? selectedLocation.name : 'Unknown Location';
    const checkInDate = checkInDateElement.value;
    const checkInTime = checkInTimeElement.value;
    const checkOutDate = checkOutDateElement.value;
    const checkOutTime = checkOutTimeElement.value;
    const promoCode = promoCodeElement ? promoCodeElement.value : '';

    if (!locationId || !checkInDate || !checkInTime || !checkOutDate || !checkOutTime) {
      alert("Please fill in all required fields.");
      return;
    }

    // Show spinner and disable the button while processing
    const bookButton = document.getElementById("book-button");
    const spinner = document.getElementById("spinner");
    const buttonText = document.getElementById("button-text");

    if (!bookButton || !spinner || !buttonText) {
      return; // Button elements not found, exit
    }

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
        if (data.error) {
          alert(data.error);
          return;
        }

        console.log("Booking created:", data);

        // Update modal content with the booking details
        document.getElementById("modal-location").textContent = locationName;
        document.getElementById("modal-checkin").textContent = `${checkInDate} ${checkInTime}`;
        document.getElementById("modal-checkout").textContent = `${checkOutDate} ${checkOutTime}`;
        document.getElementById("modal-promo").textContent = promoCode;
        document.getElementById("modal-reference").textContent = data.booking_reference;
        document.getElementById("modal-price").textContent = `KES ${data.total_price.toFixed(2)}`;

        // Show payment section if payment is required
        if (data.requires_payment) {
          const paymentSection = document.getElementById("payment-section");
          paymentSection.classList.remove("d-none");

          // Store booking ID for payment
          paymentSection.dataset.bookingId = data.booking_id;

          // Setup payment button handler
          setupPaymentHandler();
        }

        // Show the Bootstrap modal
        let bookingModal = new bootstrap.Modal(document.getElementById("bookingModal"));
        bookingModal.show();
      })
      .catch(error => {
        console.error("Error booking parking:", error);
        alert("Booking failed. Please try again.");
      })
      .finally(() => {
        // Hide spinner and re-enable the button regardless of outcome
        bookButton.disabled = false;
        spinner.classList.add("d-none");
        buttonText.textContent = "Book Now";
      });
  });
}

// Payment handler
function setupPaymentHandler() {
  const payNowBtn = document.getElementById("pay-now-btn");
  const paymentPhone = document.getElementById("payment-phone");
  const paymentSection = document.getElementById("payment-section");

  // Remove existing listeners
  const newPayNowBtn = payNowBtn.cloneNode(true);
  payNowBtn.parentNode.replaceChild(newPayNowBtn, payNowBtn);

  newPayNowBtn.addEventListener("click", function () {
    const phoneNumber = paymentPhone.value.trim();
    const bookingId = paymentSection.dataset.bookingId;

    if (!phoneNumber) {
      alert("Please enter your M-Pesa phone number");
      return;
    }

    // Validate phone number format
    const phonePattern = /^(07|254)[0-9]{8,9}$/;
    if (!phonePattern.test(phoneNumber)) {
      alert("Invalid phone number format. Use 07XXXXXXXX or 2547XXXXXXXX");
      return;
    }

    initiatePayment(bookingId, phoneNumber);
  });
}

// Initiate M-Pesa payment
function initiatePayment(bookingId, phoneNumber) {
  const payNowBtn = document.getElementById("pay-now-btn");
  const paySpinner = document.getElementById("pay-spinner");
  const payText = document.getElementById("pay-text");
  const paymentPhone = document.getElementById("payment-phone");

  // Disable button and show spinner
  payNowBtn.disabled = true;
  paySpinner.classList.remove("d-none");
  payText.textContent = "Initiating...";
  paymentPhone.disabled = true;

  fetch("/api/payment/initiate", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      booking_id: bookingId,
      phone_number: phoneNumber
    })
  })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        showPaymentStatus("info", "Payment request sent! Please check your phone and enter your M-Pesa PIN.");
        showPaymentProgress(true);

        // Start polling for payment status
        pollPaymentStatus(bookingId, 0);
      } else {
        showPaymentStatus("danger", data.error || "Payment initiation failed. Please try again.");
        resetPaymentButton();
      }
    })
    .catch(error => {
      console.error("Error initiating payment:", error);
      showPaymentStatus("danger", "Network error. Please try again.");
      resetPaymentButton();
    });
}

// Poll payment status
function pollPaymentStatus(bookingId, attempts) {
  const maxAttempts = 10; // 10 attempts * 3 seconds = 30 seconds

  if (attempts >= maxAttempts) {
    showPaymentStatus("warning", "Payment is taking longer than expected. Please check your dashboard for booking status.");
    showPaymentProgress(false);
    resetPaymentButton();
    return;
  }

  setTimeout(() => {
    fetch(`/api/booking/${bookingId}/status`)
      .then(response => response.json())
      .then(data => {
        if (data.error) {
          showPaymentStatus("danger", data.error);
          showPaymentProgress(false);
          resetPaymentButton();
          return;
        }

        if (data.payment_status === "completed") {
          showPaymentStatus("success", "✓ Payment successful! Your booking is confirmed.");
          showPaymentProgress(false);
          document.getElementById("payment-section").classList.add("d-none");
          document.getElementById("modal-close-btn").textContent = "Done";
        } else if (data.payment_status === "failed") {
          showPaymentStatus("danger", `Payment failed: ${data.payment_result_desc || "Unknown error"}`);
          showPaymentProgress(false);
          resetPaymentButton();
        } else if (data.payment_status === "pending") {
          // Continue polling
          pollPaymentStatus(bookingId, attempts + 1);
        } else {
          showPaymentStatus("warning", `Payment status: ${data.payment_status}`);
          showPaymentProgress(false);
          resetPaymentButton();
        }
      })
      .catch(error => {
        console.error("Error checking payment status:", error);
        // Continue polling on error
        pollPaymentStatus(bookingId, attempts + 1);
      });
  }, 3000); // Poll every 3 seconds
}

// Show payment status message
function showPaymentStatus(type, message) {
  const statusDiv = document.getElementById("payment-status");
  const alertDiv = document.getElementById("payment-alert");

  statusDiv.classList.remove("d-none");
  alertDiv.className = `alert alert-${type}`;
  alertDiv.textContent = message;
}

// Show/hide payment progress bar
function showPaymentProgress(show) {
  const progressDiv = document.getElementById("payment-progress");
  if (show) {
    progressDiv.classList.remove("d-none");
  } else {
    progressDiv.classList.add("d-none");
  }
}

// Reset payment button
function resetPaymentButton() {
  const payNowBtn = document.getElementById("pay-now-btn");
  const paySpinner = document.getElementById("pay-spinner");
  const payText = document.getElementById("pay-text");
  const paymentPhone = document.getElementById("payment-phone");

  if (payNowBtn) payNowBtn.disabled = false;
  if (paySpinner) paySpinner.classList.add("d-none");
  if (payText) payText.textContent = "Pay with M-Pesa";
  if (paymentPhone) paymentPhone.disabled = false;
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