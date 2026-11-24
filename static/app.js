// Interactive frontend script for dynamic slot fetching, hold countdown timers, and checkout.

document.addEventListener('DOMContentLoaded', () => {
  initBookingPage();
  initCheckoutPage();
});

function initBookingPage() {
  // Wire up service selection, date change listeners, and dynamic slot rendering.
  const serviceSelect = document.getElementById('serviceSelect');
  const dateInput = document.getElementById('bookingDate');
  const slotsContainer = document.getElementById('slotsContainer');
  const selectedSlotInput = document.getElementById('selectedSlotId');
  const submitBtn = document.getElementById('continueCheckoutBtn');
  const emptyNotice = document.getElementById('slotsEmptyNotice');

  if (!serviceSelect || !dateInput || !slotsContainer) return;

  async function fetchSlots() {
    // Query backend API for real-time open and booked slots for selected service and date.
    const serviceId = serviceSelect.value;
    const dateVal = dateInput.value;
    if (!serviceId || !dateVal) return;

    slotsContainer.innerHTML = '<div style="padding:1rem;color:#64748b;">Loading available slots...</div>';
    if (selectedSlotInput) selectedSlotInput.value = '';
    if (submitBtn) submitBtn.disabled = true;

    try {
      const res = await fetch(`/api/slots?service_id=${serviceId}&date=${dateVal}`);
      const data = await res.json();

      slotsContainer.innerHTML = '';
      if (!data.slots || data.slots.length === 0) {
        slotsContainer.innerHTML = '<div style="padding:1rem;color:#64748b;">No shoot slots configured for this date. Please pick another date.</div>';
        return;
      }

      data.slots.forEach(slot => {
        const pill = document.createElement('div');
        pill.className = `slot-pill ${slot.is_available ? '' : 'disabled'}`;
        pill.innerHTML = `
          <div class="slot-time">${slot.start_time} - ${slot.end_time}</div>
          <div class="slot-status">${slot.is_available ? 'Available' : 'Booked / Full'}</div>
        `;

        if (slot.is_available) {
          pill.addEventListener('click', () => {
            document.querySelectorAll('.slot-pill').forEach(el => el.classList.remove('selected'));
            pill.classList.add('selected');
            if (selectedSlotInput) selectedSlotInput.value = slot.id;
            if (submitBtn) submitBtn.disabled = false;
          });
        }
        slotsContainer.appendChild(pill);
      });
    } catch (err) {
      slotsContainer.innerHTML = '<div style="padding:1rem;color:#dc2626;">Error loading slots. Please refresh and try again.</div>';
    }
  }

  // Populate quick 7-day selector strip
  const dateStrip = document.getElementById('quickDateStrip');
  if (dateStrip) {
    const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const today = new Date();

    for (let i = 0; i < 7; i++) {
      const d = new Date(today);
      d.setDate(today.getDate() + i);

      const yyyy = d.getFullYear();
      const mm = String(d.getMonth() + 1).padStart(2, '0');
      const dd = String(d.getDate()).padStart(2, '0');
      const isoDate = `${yyyy}-${mm}-${dd}`;

      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = `filter-pill ${i === 0 ? 'active' : ''}`;
      chip.style.textAlign = 'center';
      chip.style.padding = '0.4rem 0.75rem';

      const label = i === 0 ? 'Today' : (i === 1 ? 'Tomorrow' : `${days[d.getDay()]}, ${d.getDate()} ${months[d.getMonth()]}`);
      chip.innerHTML = label;

      chip.addEventListener('click', () => {
        dateStrip.querySelectorAll('.filter-pill').forEach(el => el.classList.remove('active'));
        chip.classList.add('active');
        dateInput.value = isoDate;
        fetchSlots();
      });

      dateStrip.appendChild(chip);
    }
  }

  serviceSelect.addEventListener('change', fetchSlots);
  dateInput.addEventListener('change', fetchSlots);

  // Trigger initial fetch if fields are pre-populated
  if (serviceSelect.value && dateInput.value) {
    fetchSlots();
  }
}

function initCheckoutPage() {
  // Start checkout hold countdown timer and attach Razorpay modal triggers.
  const timerElement = document.getElementById('countdownTimer');
  if (!timerElement) return;

  let secondsLeft = parseInt(timerElement.dataset.seconds || '600', 10);

  const interval = setInterval(() => {
    // Tick down hold seconds and auto-expire reservation upon hitting zero.
    if (secondsLeft <= 0) {
      clearInterval(interval);
      timerElement.textContent = '00:00';
      alert('Your 10-minute hold reservation has expired. The slot has been released for other creators.');
      window.location.href = '/book';
      return;
    }

    const minutes = Math.floor(secondsLeft / 60);
    const secs = secondsLeft % 60;
    timerElement.textContent = `${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    secondsLeft -= 1;
  }, 1000);
}

function processPayment(orderId, amountPaise, keyId, bookingRef, customerName, customerEmail, customerPhone) {
  // Launch standard Razorpay checkout modal or fallback to simulation verification.
  if (orderId.startsWith('order_mock_') || typeof Razorpay === 'undefined') {
    simulateSuccessPayment(orderId, bookingRef);
    return;
  }

  const options = {
    key: keyId,
    amount: amountPaise,
    currency: 'INR',
    name: 'SpotMyShoot',
    description: `Shoot Space Reservation: ${bookingRef}`,
    order_id: orderId,
    handler: function (response) {
      // Forward Razorpay verification payload to server endpoint
      submitPaymentVerification(
        bookingRef,
        response.razorpay_order_id,
        response.razorpay_payment_id,
        response.razorpay_signature
      );
    },
    prefill: {
      name: customerName,
      email: customerEmail,
      contact: customerPhone
    },
    theme: {
      color: '#2563eb'
    }
  };

  const rzp = new Razorpay(options);
  rzp.on('payment.failed', function (response) {
    alert(`Payment failed: ${response.error.description || 'Transaction unsuccessful'}`);
  });
  rzp.open();
}

function simulateSuccessPayment(orderId, bookingRef) {
  // Submit automated test payment credentials to verify end-to-end checkout flow.
  submitPaymentVerification(
    bookingRef,
    orderId,
    `pay_mock_${Date.now()}`,
    'mock_sig_valid'
  );
}

function submitPaymentVerification(bookingRef, orderId, paymentId, signature) {
  // Post transaction parameters to backend verification route to finalize booking confirmation.
  const form = document.createElement('form');
  form.method = 'POST';
  form.action = '/checkout/verify';

  const fields = {
    booking_reference: bookingRef,
    razorpay_order_id: orderId,
    razorpay_payment_id: paymentId,
    razorpay_signature: signature
  };

  for (const key in fields) {
    const input = document.createElement('input');
    input.type = 'hidden';
    input.name = key;
    input.value = fields[key];
    form.appendChild(input);
  }

  document.body.appendChild(form);
  form.submit();
}
