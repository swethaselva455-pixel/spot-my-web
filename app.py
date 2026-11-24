from datetime import datetime, date, timedelta, timezone
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, abort
from config import Config
from models import db, Service, Slot, Booking, Payment, AdminUser
from services.availability import get_slots_for_date, is_slot_available_for_booking, toggle_slot_block, release_expired_holds
from services.booking_service import create_checkout_hold, get_booking_details
from services.payment_service import create_payment_order, confirm_payment, verify_webhook_signature
from services.cancellation_service import calculate_refund_preview, cancel_customer_booking, admin_cancel_booking
from services.notification_service import send_booking_confirmation_email, send_cancellation_email
from services.scheduler_service import init_scheduler

def create_app():
    # Construct, configure, and initialize the core Flask application.
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    @app.context_processor
    def inject_global_template_variables():
        # Inject business settings and dynamic configuration into all template contexts.
        return {
            'config': Config,
            'now': datetime.now(timezone.utc)
        }

    return app

app = create_app()

def login_required(f):
    # Decorator to restrict administrative endpoints to authenticated sessions.
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash('Please log in with administrator credentials to access this area.', 'warning')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# ----------------- PUBLIC PAGES & BOOKING FLOW -----------------

@app.route('/')
def index():
    # Render homepage with featured shoot spaces and dynamic workflow guide.
    services = Service.query.filter_by(is_active=True).all()
    return render_template('index.html', services=services)

@app.route('/services')
@app.route('/locations')
def services_page():
    # Display full catalog of bookable photo and film studios.
    services = Service.query.filter_by(is_active=True).all()
    return render_template('services.html', services=services)

@app.route('/space/<int:service_id>')
@app.route('/location/<int:service_id>')
def space_detail(service_id):
    # Render detailed property showcase with photo gallery, amenities, and booking widget.
    service = db.session.get(Service, service_id)
    if not service or not service.is_active:
        flash('Location space not found or currently inactive.', 'error')
        return redirect(url_for('services_page'))

    min_date = date.today().strftime('%Y-%m-%d')
    max_date = (date.today() + timedelta(days=30)).strftime('%Y-%m-%d')
    return render_template(
        'space_detail.html',
        service=service,
        min_date=min_date,
        max_date=max_date
    )

@app.route('/book')
def book_page():
    # Render calendar date picker and interactive time slot scheduler.
    services = Service.query.filter_by(is_active=True).all()
    selected_service_id = request.args.get('service_id', type=int) or (services[0].id if services else None)
    min_date = date.today().strftime('%Y-%m-%d')
    max_date = (date.today() + timedelta(days=30)).strftime('%Y-%m-%d')
    return render_template(
        'book.html',
        services=services,
        selected_service_id=selected_service_id,
        min_date=min_date,
        max_date=max_date
    )

@app.route('/api/slots')
def api_get_slots():
    # Provide AJAX JSON endpoint delivering live availability for a service and date.
    service_id = request.args.get('service_id', type=int)
    date_str = request.args.get('date', type=str)
    if not service_id or not date_str:
        return jsonify({'error': 'Missing service_id or date parameter'}), 400

    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Expected YYYY-MM-DD'}), 400

    slots = get_slots_for_date(service_id, target_date)
    return jsonify({'service_id': service_id, 'date': date_str, 'slots': slots})

@app.route('/book', methods=['POST'])
def initiate_booking():
    # Reserve chosen slot with a 10-minute hold lock and advance user to checkout.
    service_id = request.form.get('service_id', type=int)
    slot_id = request.form.get('slot_id', type=int)
    customer_name = request.form.get('customer_name', '').strip()
    customer_email = request.form.get('customer_email', '').strip()
    customer_phone = request.form.get('customer_phone', '').strip()

    if not all([service_id, slot_id, customer_name, customer_email, customer_phone]):
        flash('Please fill in all required customer and slot fields.', 'error')
        return redirect(url_for('book_page', service_id=service_id))

    success, message, booking = create_checkout_hold(
        service_id, slot_id, customer_name, customer_email, customer_phone
    )

    if not success:
        flash(message, 'error')
        return redirect(url_for('book_page', service_id=service_id))

    return redirect(url_for('checkout_page', booking_reference=booking.booking_reference))

@app.route('/checkout/<booking_reference>')
def checkout_page(booking_reference):
    # Render checkout summary with 10-minute hold countdown timer and Razorpay order.
    booking, remaining_seconds = get_booking_details(booking_reference)
    if not booking:
        flash('Booking reference not found.', 'error')
        return redirect(url_for('book_page'))

    if booking.status == 'confirmed':
        return redirect(url_for('payment_success_page', booking_reference=booking.booking_reference))

    if booking.status == 'cancelled' or remaining_seconds <= 0:
        flash('Your 10-minute checkout hold expired. The slot has been released. Please reselect your slot.', 'warning')
        return redirect(url_for('book_page', service_id=booking.service_id))

    order = create_payment_order(booking)
    return render_template(
        'checkout.html',
        booking=booking,
        order=order,
        remaining_seconds=remaining_seconds
    )

@app.route('/checkout/verify', methods=['POST'])
def verify_payment_route():
    # Validate cryptographic signature, update transaction records, and confirm booking.
    booking_reference = request.form.get('booking_reference')
    razorpay_order_id = request.form.get('razorpay_order_id')
    razorpay_payment_id = request.form.get('razorpay_payment_id')
    razorpay_signature = request.form.get('razorpay_signature')

    if not all([booking_reference, razorpay_order_id, razorpay_payment_id, razorpay_signature]):
        flash('Payment verification failed: Incomplete transaction tokens received.', 'error')
        return redirect(url_for('book_page'))

    success, message, booking = confirm_payment(
        booking_reference, razorpay_order_id, razorpay_payment_id, razorpay_signature
    )

    if not success:
        flash(f'Payment could not be confirmed: {message}', 'error')
        return redirect(url_for('checkout_page', booking_reference=booking_reference))

    # Send instant confirmation email
    send_booking_confirmation_email(booking)

    flash('Payment confirmed successfully! Your booking receipt has been generated.', 'success')
    return redirect(url_for('payment_success_page', booking_reference=booking.booking_reference))

@app.route('/booking/confirmed/<booking_reference>')
def payment_success_page(booking_reference):
    # Render confirmation receipt screen after successful payment verification.
    booking = Booking.query.filter_by(booking_reference=booking_reference).first()
    if not booking or booking.status != 'confirmed':
        flash('No confirmed booking matching reference found.', 'error')
        return redirect(url_for('index'))
    return render_template('payment_success.html', booking=booking)

@app.route('/webhook/razorpay', methods=['POST'])
def razorpay_webhook():
    # Asynchronously process verified server-to-server Razorpay webhook events.
    signature = request.headers.get('X-Razorpay-Signature', '')
    if not verify_webhook_signature(request.data, signature):
        abort(400)

    event_data = request.get_json(silent=True) or {}
    event_type = event_data.get('event')

    if event_type == 'payment.captured':
        payment_entity = event_data.get('payload', {}).get('payment', {}).get('entity', {})
        order_id = payment_entity.get('order_id')
        payment_id = payment_entity.get('id')
        payment = Payment.query.filter_by(razorpay_order_id=order_id).first()
        if payment and payment.booking and payment.booking.status == 'pending':
            payment.status = 'paid'
            payment.razorpay_payment_id = payment_id
            payment.booking.status = 'confirmed'
            payment.booking.hold_expires_at = None
            db.session.commit()
            send_booking_confirmation_email(payment.booking)

    return jsonify({'status': 'webhook processed'}), 200

# ----------------- MY BOOKING & CANCELLATION -----------------

@app.route('/my-booking')
def my_booking_page():
    # Look up booking details and evaluate eligible refund percentage under cancellation policy.
    search_id = request.args.get('booking_id', '').strip()
    search_email = request.args.get('email', '').strip()

    booking = None
    refund_amount = 0.0
    refund_tier_label = ""

    if search_id and search_email:
        release_expired_holds()
        booking = Booking.query.filter(
            Booking.booking_reference == search_id.upper(),
            Booking.customer_email == search_email.lower()
        ).first()
        if booking and booking.status == 'confirmed':
            refund_amount, refund_tier_label = calculate_refund_preview(booking)

    return render_template(
        'my_booking.html',
        booking=booking,
        search_id=search_id,
        search_email=search_email,
        refund_amount=refund_amount,
        refund_tier_label=refund_tier_label
    )

@app.route('/my-booking/cancel', methods=['POST'])
def cancel_booking_action():
    # Process self-service booking cancellation, trigger refund, and release time slot.
    booking_reference = request.form.get('booking_reference', '').strip()
    customer_email = request.form.get('customer_email', '').strip()

    success, message, booking = cancel_customer_booking(booking_reference, customer_email)
    if not success:
        flash(message, 'error')
    else:
        send_cancellation_email(booking, booking.refund_amount)
        flash(message, 'success')

    return redirect(url_for('my_booking_page', booking_id=booking_reference, email=customer_email))

# ----------------- ADMIN DASHBOARD & MANAGEMENT -----------------

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    # Authenticate administrator credentials against hashed password records.
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        admin = AdminUser.query.filter_by(username=username).first()
        if admin and admin.check_password(password) and admin.is_active:
            session['admin_logged_in'] = True
            session['admin_username'] = admin.username
            flash(f'Welcome back, {admin.username}!', 'success')
            return redirect(url_for('admin_dashboard'))
        flash('Invalid administrator username or password.', 'error')

    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    # Terminate administrator session and return to home screen.
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    flash('You have been logged out of the admin console.', 'info')
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    # Render operational dashboard with booking metrics, slot blocker, and revenue statistics.
    release_expired_holds()

    filter_status = request.args.get('status', '').strip()
    filter_date = request.args.get('date', '').strip()

    query = Booking.query.order_by(Booking.created_at.desc())
    if filter_status:
        query = query.filter(Booking.status == filter_status)
    if filter_date:
        try:
            d_obj = datetime.strptime(filter_date, '%Y-%m-%d').date()
            query = query.join(Slot).filter(Slot.slot_date == d_obj)
        except ValueError:
            pass

    bookings = query.all()

    # Revenue metrics
    confirmed_bookings = Booking.query.filter_by(status='confirmed').all()
    total_revenue = sum(b.total_amount for b in confirmed_bookings)
    total_bookings = Booking.query.count()
    confirmed_count = len(confirmed_bookings)
    pending_count = Booking.query.filter_by(status='pending').count()
    cancelled_count = Booking.query.filter_by(status='cancelled').count()

    # Slot management
    services = Service.query.filter_by(is_active=True).all()
    selected_service_id = request.args.get('slot_service_id', type=int) or (services[0].id if services else None)
    selected_slot_date = request.args.get('slot_date', date.today().strftime('%Y-%m-%d'))
    try:
        s_date_obj = datetime.strptime(selected_slot_date, '%Y-%m-%d').date()
    except ValueError:
        s_date_obj = date.today()

    managed_slots = Slot.query.filter_by(
        service_id=selected_service_id, slot_date=s_date_obj
    ).order_by(Slot.start_time).all()

    return render_template(
        'admin_dashboard.html',
        bookings=bookings,
        total_revenue=total_revenue,
        total_bookings=total_bookings,
        confirmed_count=confirmed_count,
        pending_count=pending_count,
        cancelled_count=cancelled_count,
        filter_status=filter_status,
        filter_date=filter_date,
        services=services,
        selected_service_id=selected_service_id,
        selected_slot_date=selected_slot_date,
        managed_slots=managed_slots
    )

@app.route('/admin/slots/toggle', methods=['POST'])
@login_required
def admin_toggle_slot():
    # Toggle active blocked state for an individual slot window.
    slot_id = request.form.get('slot_id', type=int)
    service_id = request.form.get('service_id', type=int)
    date_val = request.form.get('date', '')

    new_status = toggle_slot_block(slot_id)
    if new_status is not None:
        flash(f'Slot status updated to {"Blocked" if new_status else "Available"}.', 'success')
    else:
        flash('Could not find slot to update.', 'error')

    return redirect(url_for('admin_dashboard', slot_service_id=service_id, slot_date=date_val) + '#slots-section')

@app.route('/admin/slots/add', methods=['POST'])
@login_required
def admin_add_slot():
    # Create an individual custom slot with designated capacity and timings.
    service_id = request.form.get('service_id', type=int)
    date_str = request.form.get('slot_date', '').strip()
    start_time = request.form.get('start_time', '').strip()
    end_time = request.form.get('end_time', '').strip()
    capacity = request.form.get('capacity', type=int) or 1

    try:
        slot_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        new_slot = Slot(
            service_id=service_id,
            slot_date=slot_date,
            start_time=start_time,
            end_time=end_time,
            capacity=capacity,
            is_blocked=False
        )
        db.session.add(new_slot)
        db.session.commit()
        flash(f'New slot added for {date_str} ({start_time} - {end_time}).', 'success')
    except Exception as e:
        flash(f'Error creating slot: {str(e)}', 'error')

    return redirect(url_for('admin_dashboard', slot_service_id=service_id, slot_date=date_str) + '#slots-section')

@app.route('/admin/cancel', methods=['POST'])
@login_required
def admin_cancel_route():
    # Process administrator override to cancel booking and disburse designated refund.
    booking_id = request.form.get('booking_id', type=int)
    refund_pct = request.form.get('refund_percentage', 100.0, type=float)

    success, message, booking = admin_cancel_booking(booking_id, refund_pct, "Admin dashboard cancellation")
    if success:
        send_cancellation_email(booking, booking.refund_amount)
        flash(message, 'success')
    else:
        flash(message, 'error')

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/export/csv')
@login_required
def admin_export_csv():
    # Stream bookings database records as a downloadable CSV report for external accounting.
    import csv
    import io
    from flask import Response

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Booking Reference', 'Customer Name', 'Email', 'Phone',
        'Service / Location', 'Date', 'Time Slot',
        'Subtotal (INR)', 'Tax (INR)', 'Total Amount (INR)',
        'Status', 'Refund Amount (INR)', 'Created At UTC'
    ])

    bookings = Booking.query.order_by(Booking.created_at.desc()).all()
    for b in bookings:
        service_name = b.service.name if b.service else 'N/A'
        slot_date = b.slot.slot_date.strftime('%Y-%m-%d') if b.slot else 'N/A'
        slot_time = f"{b.slot.start_time} - {b.slot.end_time}" if b.slot else 'N/A'
        created_str = b.created_at.strftime('%Y-%m-%d %H:%M:%S') if b.created_at else ''

        writer.writerow([
            b.booking_reference, b.customer_name, b.customer_email, b.customer_phone,
            service_name, slot_date, slot_time,
            f"{b.subtotal:.2f}", f"{b.tax_amount:.2f}", f"{b.total_amount:.2f}",
            b.status, f"{b.refund_amount:.2f}", created_str
        ])

    csv_data = output.getvalue()
    filename = f"spotmyshoot_bookings_{date.today().strftime('%Y%m%d')}.csv"
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

@app.route('/admin/slots/generate-batch', methods=['POST'])
@login_required
def admin_generate_batch_slots():
    # Batch create open daily calendar slots across a custom future date range.
    from services.availability import generate_slots

    service_id = request.form.get('service_id', type=int)
    start_date_str = request.form.get('start_date', '').strip()
    end_date_str = request.form.get('end_date', '').strip()
    capacity = request.form.get('capacity', 1, type=int)

    default_timings = [
        ("09:00", "11:00"),
        ("11:30", "13:30"),
        ("14:30", "16:30"),
        ("17:00", "19:00")
    ]

    try:
        s_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        e_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        if e_date < s_date:
            flash('End date must be greater than or equal to start date.', 'error')
            return redirect(url_for('admin_dashboard') + '#slots-section')

        created = generate_slots(service_id, s_date, e_date, default_timings, capacity)
        flash(f'Successfully generated {created} new slots between {start_date_str} and {end_date_str}.', 'success')
    except Exception as e:
        flash(f'Batch generation failed: {str(e)}', 'error')

    return redirect(url_for('admin_dashboard', slot_service_id=service_id, slot_date=start_date_str) + '#slots-section')

# ----------------- ERROR HANDLERS -----------------

@app.errorhandler(404)
def not_found_error(error):
    # Handle missing page routes with user-friendly error display.
    return render_template('base.html'), 404

@app.errorhandler(500)
def internal_error(error):
    # Handle unexpected server errors and rollback database session.
    db.session.rollback()
    return render_template('base.html'), 500

if __name__ == '__main__':
    # Initialize background scheduler and run application on configured port.
    with app.app_context():
        db.create_all()
    init_scheduler(app)
    app.run(host='0.0.0.0', port=int(Config.PORT or 5000), debug=True)
