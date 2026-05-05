from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Event, EventCoreUser


class EventDiscoveryTests(TestCase):
    def setUp(self):
        self.auth_user = User.objects.create_user(username='organizer', password='secret123')
        EventCoreUser.objects.create(
            auth_user=self.auth_user,
            first_name='Ora',
            last_name='Ganizer',
            email='organizer@example.com',
            role=EventCoreUser.ROLE_ORGANIZER,
        )
        self.client.force_login(self.auth_user)
        self.now = timezone.now()

        self.cleanup = Event.objects.create(
            title='Riverside Clean-up',
            event_type=Event.TYPE_CLEANUP,
            description='Community clean-up along the river.',
            location='Riverside',
            start_datetime=self.now + timedelta(days=2),
            end_datetime=self.now + timedelta(days=2, hours=3),
            capacity=30,
            budget=5000,
            status=Event.STATUS_PLANNED,
        )
        self.medical = Event.objects.create(
            title='Health Check Mission',
            event_type=Event.TYPE_MEDICAL,
            description='Free health checks for residents.',
            location='Barangay Hall',
            start_datetime=self.now + timedelta(days=5),
            end_datetime=self.now + timedelta(days=5, hours=4),
            capacity=80,
            budget=15000,
            status=Event.STATUS_PLANNED,
        )
        self.active = Event.objects.create(
            title='Active Assembly',
            event_type=Event.TYPE_ASSEMBLY,
            description='Assembly happening now.',
            location='Covered Court',
            start_datetime=self.now - timedelta(hours=1),
            end_datetime=self.now + timedelta(hours=2),
            capacity=100,
            budget=1000,
            status=Event.STATUS_ONGOING,
        )
        self.overdue = Event.objects.create(
            title='Old Feeding Program',
            event_type=Event.TYPE_FEEDING,
            description='Past event still awaiting final status.',
            location='Day Care Center',
            start_datetime=self.now - timedelta(days=3),
            end_datetime=self.now - timedelta(days=3, hours=-2),
            capacity=40,
            budget=3000,
            status=Event.STATUS_PLANNED,
        )

    def test_event_list_filters_by_timeframe_and_marks_overdue_events(self):
        response = self.client.get(reverse('event_list'), {'timeframe': 'overdue'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Old Feeding Program')
        self.assertContains(response, 'Needs review')
        self.assertNotContains(response, 'Riverside Clean-up')
        self.assertEqual(response.context['selected_timeframe'], 'overdue')

    def test_event_list_sorts_by_capacity(self):
        response = self.client.get(reverse('event_list'), {'sort': 'capacity'})

        events = response.context['events']
        self.assertEqual(events[0], self.active)
        self.assertEqual(response.context['selected_sort'], 'capacity')

    def test_dashboard_surfaces_active_and_overdue_counts(self):
        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['stats']['active_events'], 1)
        self.assertEqual(response.context['stats']['overdue_events'], 1)
        self.assertContains(response, 'Happening Now')
        self.assertContains(response, 'Needs Status Review')
