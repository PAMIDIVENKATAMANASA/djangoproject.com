import json
import os
from datetime import date, timedelta
from decimal import Decimal
from functools import partial
from unittest.mock import patch

import stripe
from django.conf import settings
from django.core import mail
from django.core.urlresolvers import reverse
from django.test import TestCase
from django_hosts.resolvers import reverse as django_hosts_reverse
from PIL import Image

from .exceptions import DonationError
from .forms import PaymentForm
from .models import GOAL_START_DATE, DjangoHero, Donation, Payment
from .templatetags.fundraising_extras import donation_form_with_heart


def _fake_random(*results):
    """
    Return a callable that generates the given results when called.
    Useful for mocking random.random().

    Example:

    >>> r = _fake_random(1, 2, 3)
    >>> r()
    1
    >>> r()
    2
    >>> r()
    3
    """
    return partial(next, iter(results))


class TestIndex(TestCase):
    def test_redirect(self):
        response = self.client.get(reverse('fundraising:index'))
        self.assertEqual(response.status_code, 200)


class TestCampaign(TestCase):
    def setUp(self):
        self.index_url = reverse('fundraising:index')

    def test_donors_count(self):
        # Donor with a Payment after GOAL_START_DATE
        donor1 = DjangoHero.objects.create()
        donation1 = donor1.donation_set.create()
        donation1.payment_set.create(amount=1, stripe_charge_id='a')
        donation1.payment_set.create(amount=2, stripe_charge_id='b')
        # Donor with a Payment before GOAL_START_DATE
        past_donor = DjangoHero.objects.create()
        past_donation = past_donor.donation_set.create()
        past_payment = past_donation.payment_set.create(amount=4, stripe_charge_id='c')
        Payment.objects.filter(pk=past_payment.pk).update(date=GOAL_START_DATE - timedelta(days=1))
        response = donation_form_with_heart({'user': None})
        self.assertEqual(response['total_donors'], 1)
        self.assertEqual(response['donated_amount'], Decimal('3.00'))

    def test_anonymous_donor(self):
        hero = DjangoHero.objects.create(
            is_visible=True, approved=True, hero_type='individual')
        Donation.objects.create(donor=hero, subscription_amount='5')
        response = self.client.get(self.index_url)
        self.assertContains(response, 'Anonymous Hero')

    def test_anonymous_donor_with_logo(self):
        hero = DjangoHero.objects.create(
            is_visible=True, approved=True,
            hero_type='individual', logo='yes')  # We don't need an actual image
        Donation.objects.create(donor=hero)
        response = self.client.get(self.index_url)
        self.assertContains(response, 'Anonymous Hero')

    def test_submitting_donation_form_missing_token(self):
        url = reverse('fundraising:donate')
        response = self.client.post(url, {'amount': 100})
        content = json.loads(response.content.decode())
        self.assertEqual(200, response.status_code)
        self.assertFalse(content['success'])

    def test_submitting_donation_form_invalid_amount(self):
        url = reverse('fundraising:donate')
        response = self.client.post(url, {
            'amount': 'superbad',
            'stripe_token': 'test',
            'interval': 'onetime',
        })
        content = json.loads(response.content.decode())
        self.assertEqual(200, response.status_code)
        self.assertFalse(content['success'])

    @patch('stripe.Customer.create')
    @patch('stripe.Charge.create')
    def test_submitting_donation_form(self, charge_create, customer_create):
        charge_create.return_value.id = 'XYZ'
        customer_create.return_value.id = '1234'
        self.client.post(reverse('fundraising:donate'), {
            'amount': 100,
            'stripe_token': 'test',
            'receipt_email': 'test@example.com',
            'interval': 'onetime',
        })
        donations = Donation.objects.all()
        self.assertEqual(donations.count(), 1)
        self.assertEqual(donations[0].subscription_amount, 100)
        self.assertEqual(donations[0].total_payments(), 100)
        self.assertEqual(donations[0].receipt_email, 'test@example.com')
        self.assertEqual(donations[0].stripe_subscription_id, '')

    @patch('stripe.Customer.create')
    @patch('stripe.Charge.create')
    def test_submitting_donation_form_recurring(self, charge_create, customer_create):
        customer_create.return_value.id = '1234'
        customer_create.return_value.subscriptions.create.return_value.id = 'XYZ'
        self.client.post(reverse('fundraising:donate'), {
            'amount': 100,
            'stripe_token': 'test',
            'receipt_email': 'test@example.com',
            'interval': 'monthly',
        })
        donations = Donation.objects.all()
        self.assertEqual(donations.count(), 1)
        self.assertEqual(donations[0].subscription_amount, 100)
        self.assertEqual(donations[0].receipt_email, 'test@example.com')
        self.assertEqual(donations[0].payment_set.count(), 0)

    @patch('stripe.Customer.create')
    @patch('stripe.Charge.create')
    def test_submitting_donation_form_onetime(self, charge_create, customer_create):
        charge_create.return_value.id = 'XYZ'
        customer_create.return_value.id = '1234'
        self.client.post(reverse('fundraising:donate'), {
            'amount': 100,
            'stripe_token': 'test',
            'interval': 'onetime',
            'receipt_email': 'django@example.com',
        })
        donations = Donation.objects.all()
        self.assertEqual(donations.count(), 1)
        self.assertEqual(donations[0].total_payments(), 100)
        self.assertEqual(donations[0].payment_set.first().stripe_charge_id, 'XYZ')

    @patch('stripe.Customer.create')
    @patch('stripe.Charge.create')
    def test_submitting_donation_form_error_handling(self, charge_create, customer_create):
        data = {
            'amount': 100,
            'stripe_token': 'xxxx',
            'interval': 'onetime',
            'receipt_email': 'django@example.com',
        }
        form = PaymentForm(data=data)

        self.assertTrue(form.is_valid())

        # some errors are shows as user facting DonationErrors to the user
        # some are bubbling up to raise a 500 to trigger Sentry reports
        errors = [
            [stripe.error.CardError, DonationError],
            [stripe.error.InvalidRequestError, DonationError],
            [stripe.error.APIConnectionError, DonationError],
            [stripe.error.AuthenticationError, None],
            [stripe.error.StripeError, None],
            [ValueError, None],
        ]

        for backend_exception, user_exception in errors:
            customer_create.side_effect = backend_exception('message', 'param', 'code')

            if user_exception is None:
                self.assertRaises(backend_exception, form.make_donation)
            else:
                response = self.client.post(reverse('fundraising:donate'), data)
                content = json.loads(response.content.decode())
                self.assertFalse(content['success'])

    @patch('fundraising.forms.PaymentForm.make_donation')
    def test_submitting_donation_form_valid(self, make_donation):
        amount = 100
        donor = DjangoHero.objects.create()
        donation = Donation.objects.create(
            donor=donor,
            stripe_customer_id='xxxx',
        )
        Payment.objects.create(
            donation=donation,
            amount=amount,
            stripe_charge_id='xxxx',
        )
        make_donation.return_value = donation
        response = self.client.post(reverse('fundraising:donate'), {
            'amount': amount,
            'stripe_token': 'xxxx',
            'interval': 'onetime',
            'receipt_email': 'django@example.com',
        })
        content = json.loads(response.content.decode())
        self.assertEquals(200, response.status_code)
        self.assertTrue(content['success'])
        self.assertEqual(content['redirect'], donation.get_absolute_url())

    @patch('stripe.Customer.retrieve')
    def test_cancel_donation(self, retrieve_customer):
        donor = DjangoHero.objects.create()
        donation = Donation.objects.create(
            donor=donor,
            stripe_subscription_id='12345', stripe_customer_id='54321',
        )
        url = reverse(
            'fundraising:cancel-donation',
            kwargs={'hero': donor.id, 'donation': donation.id}
        )
        response = self.client.get(url)
        self.assertRedirects(response, reverse('fundraising:manage-donations',
                                               kwargs={'hero': donor.id}))
        retrieve_customer.assert_called_once_with('54321')
        donation = Donation.objects.get(id=donation.id)
        self.assertEqual('', donation.stripe_subscription_id)

    @patch('stripe.Customer.retrieve')
    def test_cancel_already_cancelled_donation(self, retrieve_customer):
        donor = DjangoHero.objects.create()
        donation = Donation.objects.create(donor=donor, stripe_subscription_id='')
        url = reverse(
            'fundraising:cancel-donation',
            kwargs={'hero': donor.id, 'donation': donation.id}
        )
        response = self.client.get(url)
        self.assertEquals(404, response.status_code)
        self.assertFalse(retrieve_customer.called)


class TestDjangoHero(TestCase):
    def setUp(self):
        kwargs = {
            'approved': True,
            'is_visible': True,
        }
        self.h1 = DjangoHero.objects.create(**kwargs)
        d1 = Donation.objects.create(donor=self.h1)
        Payment.objects.create(donation=d1, amount='5', stripe_charge_id='a1')
        self.h2 = DjangoHero.objects.create(**kwargs)
        d2 = Donation.objects.create(donor=self.h2)
        Payment.objects.create(donation=d2, amount='15', stripe_charge_id='a2')
        self.h3 = DjangoHero.objects.create(**kwargs)
        d3 = Donation.objects.create(donor=self.h3)
        Payment.objects.create(donation=d3, amount='10', stripe_charge_id='a3')
        self.today = date.today()

    def test_thumbnail(self):
        try:
            os.makedirs(os.path.join(settings.MEDIA_ROOT, 'fundraising/logos/'))
        except OSError:  # directory may already exist
            pass
        image_path = os.path.join(settings.MEDIA_ROOT, 'fundraising/logos/test_logo.jpg')
        image = Image.new('L', (500, 500))
        image.save(image_path)
        self.h1.logo = image_path
        self.h1.save()
        thumbnail = self.h1.thumbnail
        self.assertEqual(thumbnail.x, 170)
        self.assertEqual(thumbnail.y, 170)
        os.remove(image_path)
        self.assertTrue(
            os.path.exists(
                thumbnail.url.replace(settings.MEDIA_URL, '{}/'.format(settings.MEDIA_ROOT))
            )
        )

    def test_thumbnail_no_logo(self):
        self.assertIsNone(self.h2.thumbnail)

    def test_name_with_fallback(self):
        hero = DjangoHero()
        self.assertEqual(hero.name_with_fallback, 'Anonymous Hero')
        hero.name = 'Batistek'
        self.assertEqual(hero.name_with_fallback, 'Batistek')


class TestPaymentForm(TestCase):
    @patch('stripe.Customer.create')
    @patch('stripe.Charge.create')
    def test_make_donation(self, charge_create, customer_create):
        customer_create.return_value.id = 'xxxx'
        charge_create.return_value.id = 'xxxx'
        form = PaymentForm(data={
            'amount': 100,
            'stripe_token': 'xxxx',
            'interval': 'onetime',
            'receipt_email': 'django@example.com',
        })
        self.assertTrue(form.is_valid())
        donation = form.make_donation()
        self.assertEqual(100, donation.payment_set.first().amount)

    @patch('stripe.Customer.retrieve')
    @patch('stripe.Charge.create')
    def test_make_donation_with_existing_hero(self, charge_create, customer_retrieve):
        charge_create.return_value.id = 'XYZ'
        customer_retrieve.return_value.id = '12345'
        hero = DjangoHero.objects.create(
            email='django@example.com',
            stripe_customer_id=customer_retrieve.return_value.id,
        )
        form = PaymentForm(data={
            'amount': 100,
            'stripe_token': 'xxxx',
            'interval': 'onetime',
            'receipt_email': 'django@example.com',
        })
        self.assertTrue(form.is_valid())
        donation = form.make_donation()
        self.assertEqual(100, donation.payment_set.first().amount)
        self.assertEqual(hero, donation.donor)
        self.assertEqual(hero.stripe_customer_id, donation.stripe_customer_id)

    @patch('stripe.Customer.create')
    @patch('stripe.Charge.create')
    def test_make_donation_exception(self, charge_create, customer_create):
        customer_create.side_effect = ValueError("Something is wrong")
        form = PaymentForm(data={
            'amount': 100,
            'stripe_token': 'xxxx',
            'interval': 'onetime',
            'receipt_email': 'django@example.com',
        })
        self.assertTrue(form.is_valid())
        with self.assertRaises(ValueError):
            donation = form.make_donation()
            self.assertIsNone(donation)


class TestThankYou(TestCase):
    def setUp(self):
        self.hero = DjangoHero.objects.create(
            email='django@example.net',
            stripe_customer_id='1234',
            name='Under Dog',
        )
        self.donation = Donation.objects.create(
            donor=self.hero,
            stripe_customer_id='cu_123',
            receipt_email='django@example.com',
        )
        Payment.objects.create(
            donation=self.donation,
            amount='20',
        )
        self.url = reverse('fundraising:thank-you', args=[self.donation.pk])
        self.hero_form_data = {
            'hero_type': DjangoHero.HERO_TYPE_CHOICES[1][0],
            'name': 'Django Inc',
        }

    def test_template(self):
        response = self.client.get(self.url)
        self.assertEqual(response.context['form'].instance, self.donation.donor)

    @patch('stripe.Customer.retrieve')
    def test_update_hero(self, retrieve_customer):
        response = self.client.post(self.url, self.hero_form_data)
        self.assertRedirects(response, reverse('fundraising:index'))
        self.hero.refresh_from_db()
        self.assertEqual(self.hero.name, self.hero_form_data['name'])

        retrieve_customer.assert_called_once_with(self.hero.stripe_customer_id)
        customer = retrieve_customer.return_value
        self.assertEqual(customer.description, self.hero.name)
        self.assertEqual(customer.email, self.hero.email)
        customer.save.assert_called_once_with()

    def test_create_hero_for_donation(self):
        with patch('stripe.Customer.retrieve'):
            response = self.client.post(self.url, self.hero_form_data)
        self.assertRedirects(response, reverse('fundraising:index'))


class TestWebhooks(TestCase):
    def setUp(self):
        self.hero = DjangoHero.objects.create(email='hero@djangoproject.com')
        self.donation = Donation.objects.create(
            donor=self.hero,
            interval='monthly',
            stripe_customer_id='cus_3MXPY5pvYMWTBf',
            stripe_subscription_id='sub_3MXPaZGXvVZSrS',
        )

    def stripe_data(self, filename):
        file_path = settings.BASE_DIR.joinpath(
            'fundraising/test_data/{}.json'.format(filename))
        with file_path.open() as f:
            data = json.load(f)
            return stripe.resource.convert_to_stripe_object(data, stripe.api_key)

    def post_event(self):
        return self.client.post(
            reverse('fundraising:receive-webhook'),
            data='{"id": "evt_12345"}',
            content_type='application/json',
        )

    @patch('stripe.Event.retrieve')
    def test_record_payment(self, event):
        event.return_value = self.stripe_data('invoice_succeeded')
        response = self.post_event()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.donation.payment_set.count(), 1)
        payment = self.donation.payment_set.first()
        self.assertEqual(payment.amount, 10)

    @patch('stripe.Event.retrieve')
    def test_subscription_cancelled(self, event):
        event.return_value = self.stripe_data('subscription_cancelled')
        self.post_event()
        donation = Donation.objects.get(id=self.donation.id)
        self.assertEqual(donation.stripe_subscription_id, '')
        self.assertEqual(len(mail.outbox), 1)
        expected_url = django_hosts_reverse('fundraising:donate')
        self.assertTrue(expected_url in mail.outbox[0].body)

    @patch('stripe.Event.retrieve')
    def test_payment_failed(self, event):
        event.return_value = self.stripe_data('payment_failed')
        self.post_event()
        self.assertEqual(len(mail.outbox), 1)
        expected_url = django_hosts_reverse('fundraising:manage-donations', kwargs={'hero': self.hero.id})
        self.assertTrue(expected_url in mail.outbox[0].body)

    @patch('stripe.Event.retrieve')
    def test_no_such_event(self, event):
        event.side_effect = stripe.error.InvalidRequestError(
            message='No such event: evt_12345',
            param='id'
        )
        response = self.post_event()
        self.assertTrue(response.status_code, 422)
