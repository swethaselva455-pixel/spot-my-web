import unittest
from datetime import date, timedelta
from app import app
from models import db, Service, Slot, Booking, Payment, AdminUser
from config import Config
from services.availability import get_slots_for_date

class TestSpotMyShootApp(unittest.TestCase):
    """End-to-end integration test suite verifying booking, payments, refunds, and admin flows."""

    def setUp(self):
        # Configure test client with application context.
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_01_public_pages(self):
        # Verify homepage, services catalog, and space detail render HTTP 200.
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'SpotMyShoot', res.data)

        res_services = self.client.get('/services')
        self.assertEqual(res_services.status_code, 200)

        res_locations = self.client.get('/locations')
        self.assertEqual(res_locations.status_code, 200)

        res_detail = self.client.get('/space/1')
        self.assertEqual(res_detail.status_code, 200)
        self.assertIn(b'About this creative space', res_detail.data)

    def test_02_availability_api(self):
        # Test dynamic slots API returns valid JSON availability.
        today_str = date.today().strftime('%Y-%m-%d')
        res = self.client.get(f'/api/slots?service_id=1&date={today_str}')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('slots', data)
        self.assertTrue(len(data['slots']) > 0)

    def test_03_booking_and_checkout_hold(self):
        # Test creating a booking hold and checkout page lock.
        with app.app_context():
            slot = Slot.query.filter_by(service_id=1, is_blocked=False).first()
            self.assertIsNotNone(slot)
            slot_id = slot.id

        post_data = {
            'service_id': 1,
            'slot_id': slot_id,
            'customer_name': 'Test Creator',
            'customer_email': 'creator@test.com',
            'customer_phone': '9876543210'
        }
        res = self.client.post('/book', data=post_data, follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn('/checkout/', res.headers['Location'])

        # Follow to checkout page
        checkout_res = self.client.get(res.headers['Location'])
        self.assertEqual(checkout_res.status_code, 200)
        self.assertIn(b'Review Booking Summary', checkout_res.data)

    def test_04_payment_verification_and_confirmation(self):
        # Test verifying payment signature and generating confirmation receipt.
        with app.app_context():
            booking = Booking.query.filter_by(customer_email='creator@test.com', status='pending').first()
            self.assertIsNotNone(booking)
            booking_ref = booking.booking_reference
            payment = Payment.query.filter_by(booking_id=booking.id).first()
            order_id = payment.razorpay_order_id if payment else 'order_mock_test123'

        verify_data = {
            'booking_reference': booking_ref,
            'razorpay_order_id': order_id,
            'razorpay_payment_id': 'pay_mock_success_777',
            'razorpay_signature': 'mock_sig_valid'
        }
        res = self.client.post('/checkout/verify', data=verify_data, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Your Shoot Space is Confirmed!', res.data)

        with app.app_context():
            confirmed_b = Booking.query.filter_by(booking_reference=booking_ref).first()
            self.assertEqual(confirmed_b.status, 'confirmed')

    def test_05_cancellation_and_refund(self):
        # Test looking up confirmed booking and executing cancellation with automated refund.
        with app.app_context():
            booking = Booking.query.filter_by(customer_email='creator@test.com', status='confirmed').first()
            self.assertIsNotNone(booking)
            ref = booking.booking_reference

        # Lookup page
        res = self.client.get(f'/my-booking?booking_id={ref}&email=creator@test.com')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Cancellation Policy', res.data)

        # Post cancellation
        cancel_data = {
            'booking_reference': ref,
            'customer_email': 'creator@test.com'
        }
        c_res = self.client.post('/my-booking/cancel', data=cancel_data, follow_redirects=True)
        self.assertEqual(c_res.status_code, 200)

        with app.app_context():
            cancelled_b = Booking.query.filter_by(booking_reference=ref).first()
            self.assertEqual(cancelled_b.status, 'cancelled')
            self.assertTrue(cancelled_b.refund_amount > 0)
            # Slot is now available again
            self.assertTrue(cancelled_b.slot.is_available())

    def test_06_admin_auth_and_dashboard(self):
        # Test admin login, dashboard statistics, and slot toggling.
        # Unauthorized access redirects to login
        res = self.client.get('/admin/dashboard')
        self.assertEqual(res.status_code, 302)

        # Login
        login_data = {
            'username': Config.ADMIN_USERNAME,
            'password': Config.ADMIN_PASSWORD
        }
        l_res = self.client.post('/admin/login', data=login_data, follow_redirects=True)
        self.assertEqual(l_res.status_code, 200)
        self.assertIn(b'Operations & Revenue Dashboard', l_res.data)

        # Toggle slot block
        with app.app_context():
            slot = Slot.query.first()
            s_id = slot.id
            init_state = slot.is_blocked

        toggle_data = {
            'slot_id': s_id,
            'service_id': 1,
            'date': date.today().strftime('%Y-%m-%d')
        }
        t_res = self.client.post('/admin/slots/toggle', data=toggle_data, follow_redirects=True)
        self.assertEqual(t_res.status_code, 200)

        with app.app_context():
            updated_slot = db.session.get(Slot, s_id)
            self.assertNotEqual(updated_slot.is_blocked, init_state)
            # Revert toggle
            updated_slot.is_blocked = init_state
            db.session.commit()

        # Test CSV export
        csv_res = self.client.get('/admin/export/csv')
        self.assertEqual(csv_res.status_code, 200)
        self.assertIn('text/csv', csv_res.headers.get('Content-Type', ''))
        self.assertIn(b'Booking Reference,Customer Name', csv_res.data)

        # Test Batch Slot Generation
        batch_data = {
            'service_id': 1,
            'start_date': (date.today() + timedelta(days=20)).strftime('%Y-%m-%d'),
            'end_date': (date.today() + timedelta(days=21)).strftime('%Y-%m-%d'),
            'capacity': 2
        }
        batch_res = self.client.post('/admin/slots/generate-batch', data=batch_data, follow_redirects=True)
        self.assertEqual(batch_res.status_code, 200)

        # Clean up test booking
        with app.app_context():
            b = Booking.query.filter_by(customer_email='creator@test.com').first()
            if b:
                for p in b.payments:
                    db.session.delete(p)
                db.session.delete(b)
                db.session.commit()

if __name__ == '__main__':
    unittest.main()
