from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Avg, Sum


class EventCoreUser(models.Model):
    ROLE_ADMIN = 'admin'
    ROLE_ORGANIZER = 'organizer'
    ROLE_VOLUNTEER = 'volunteer'
    ROLE_RESIDENT = 'resident'

    ROLE_CHOICES = [
        (ROLE_ADMIN, 'Admin'),
        (ROLE_ORGANIZER, 'Barangay Organizer'),
        (ROLE_VOLUNTEER, 'Volunteer'),
        (ROLE_RESIDENT, 'Resident / Participant'),
    ]

    auth_user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='eventcore_profile',
    )
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    email = models.EmailField(unique=True)
    contact_number = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_RESIDENT)
    date_joined = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'users'
        ordering = ['last_name', 'first_name']
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f'{self.first_name} {self.last_name} ({self.get_role_display()})'

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'


class Event(models.Model):
    TYPE_CLEANUP = 'cleanup'
    TYPE_FEEDING = 'feeding'
    TYPE_MEDICAL = 'medical'
    TYPE_SPORTS = 'sports'
    TYPE_ASSEMBLY = 'assembly'
    TYPE_SEMINAR = 'seminar'
    TYPE_OTHER = 'other'

    EVENT_TYPE_CHOICES = [
        (TYPE_CLEANUP, 'Clean-up Drive'),
        (TYPE_FEEDING, 'Feeding Program'),
        (TYPE_MEDICAL, 'Medical Mission'),
        (TYPE_SPORTS, 'Sports Tournament'),
        (TYPE_ASSEMBLY, 'Barangay Assembly'),
        (TYPE_SEMINAR, 'Disaster Preparedness Seminar'),
        (TYPE_OTHER, 'Other Community Event'),
    ]

    STATUS_PLANNED = 'planned'
    STATUS_ONGOING = 'ongoing'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_PLANNED, 'Planned'),
        (STATUS_ONGOING, 'Ongoing'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    title = models.CharField(max_length=150)
    event_type = models.CharField(max_length=30, choices=EVENT_TYPE_CHOICES)
    description = models.TextField()
    location = models.CharField(max_length=150)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    capacity = models.PositiveIntegerField(default=50)
    budget = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PLANNED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'events'
        ordering = ['-start_datetime']
        constraints = [
            models.CheckConstraint(condition=models.Q(capacity__gt=0), name='event_capacity_positive'),
            models.CheckConstraint(condition=models.Q(budget__gte=0), name='event_budget_not_negative'),
        ]

    def __str__(self):
        return self.title

    def clean(self):
        if self.start_datetime and self.end_datetime and self.end_datetime <= self.start_datetime:
            raise ValidationError({'end_datetime': 'End date and time must be later than the start date and time.'})
        if self.capacity < 1:
            raise ValidationError({'capacity': 'Capacity must be at least 1.'})
        if self.budget < 0:
            raise ValidationError({'budget': 'Budget cannot be negative.'})

    @property
    def confirmed_participants_count(self):
        return self.participants.filter(registration_status=Participant.STATUS_CONFIRMED).count()

    @property
    def waitlisted_participants_count(self):
        return self.participants.filter(registration_status=Participant.STATUS_WAITLISTED).count()

    @property
    def available_slots(self):
        return max(self.capacity - self.confirmed_participants_count, 0)

    @property
    def is_full(self):
        return self.available_slots == 0

    @property
    def total_estimated_resource_cost(self):
        return self.resources.aggregate(total=Sum('estimated_cost'))['total'] or Decimal('0.00')

    @property
    def total_actual_resource_cost(self):
        return self.resources.aggregate(total=Sum('actual_cost'))['total'] or Decimal('0.00')

    @property
    def remaining_budget(self):
        return self.budget - self.total_actual_resource_cost

    @property
    def average_rating(self):
        rating = self.feedback.aggregate(avg=Avg('rating'))['avg']
        return round(rating, 1) if rating else None


class EventOrganizer(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='organizer_assignments')
    organizer = models.ForeignKey(
        EventCoreUser,
        on_delete=models.CASCADE,
        limit_choices_to={'role': EventCoreUser.ROLE_ORGANIZER},
        related_name='organized_events',
    )
    responsibility = models.CharField(max_length=150, blank=True)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'event_organizers'
        unique_together = ['event', 'organizer']
        ordering = ['event', 'organizer']
        verbose_name = 'Event Organizer'
        verbose_name_plural = 'Event Organizers'

    def __str__(self):
        return f'{self.organizer} - {self.event}'


class Volunteer(models.Model):
    ATTENDANCE_REGISTERED = 'registered'
    ATTENDANCE_PRESENT = 'present'
    ATTENDANCE_ABSENT = 'absent'
    ATTENDANCE_EXCUSED = 'excused'

    ATTENDANCE_CHOICES = [
        (ATTENDANCE_REGISTERED, 'Registered'),
        (ATTENDANCE_PRESENT, 'Present'),
        (ATTENDANCE_ABSENT, 'Absent'),
        (ATTENDANCE_EXCUSED, 'Excused'),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='volunteers')
    user = models.ForeignKey(
        EventCoreUser,
        on_delete=models.CASCADE,
        limit_choices_to={'role': EventCoreUser.ROLE_VOLUNTEER},
        related_name='volunteer_assignments',
    )
    task_assigned = models.CharField(max_length=150, blank=True)
    attendance_status = models.CharField(
        max_length=20,
        choices=ATTENDANCE_CHOICES,
        default=ATTENDANCE_REGISTERED,
    )
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'volunteers'
        unique_together = ['event', 'user']
        ordering = ['event', 'user']

    def __str__(self):
        return f'{self.user} - {self.event}'

    def clean(self):
        if self.user and self.user.role != EventCoreUser.ROLE_VOLUNTEER:
            raise ValidationError({'user': 'Only users with the Volunteer role can be assigned as volunteers.'})


class Participant(models.Model):
    STATUS_CONFIRMED = 'confirmed'
    STATUS_WAITLISTED = 'waitlisted'
    STATUS_CANCELLED = 'cancelled'

    REGISTRATION_STATUS_CHOICES = [
        (STATUS_CONFIRMED, 'Confirmed'),
        (STATUS_WAITLISTED, 'Waitlisted'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    ATTENDANCE_REGISTERED = 'registered'
    ATTENDANCE_PRESENT = 'present'
    ATTENDANCE_ABSENT = 'absent'
    ATTENDANCE_LATE = 'late'

    ATTENDANCE_CHOICES = [
        (ATTENDANCE_REGISTERED, 'Registered'),
        (ATTENDANCE_PRESENT, 'Present'),
        (ATTENDANCE_ABSENT, 'Absent'),
        (ATTENDANCE_LATE, 'Late'),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(
        EventCoreUser,
        on_delete=models.CASCADE,
        limit_choices_to={'role': EventCoreUser.ROLE_RESIDENT},
        related_name='event_registrations',
    )
    attendance_status = models.CharField(
        max_length=20,
        choices=ATTENDANCE_CHOICES,
        default=ATTENDANCE_REGISTERED,
    )
    registration_status = models.CharField(
        max_length=20,
        choices=REGISTRATION_STATUS_CHOICES,
        default=STATUS_CONFIRMED,
    )
    waitlist_position = models.PositiveIntegerField(null=True, blank=True)
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'participants'
        unique_together = ['event', 'user']
        ordering = ['event', 'user']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(waitlist_position__isnull=True) | models.Q(waitlist_position__gt=0),
                name='participant_waitlist_position_positive',
            ),
        ]

    def __str__(self):
        return f'{self.user} - {self.event}'

    def clean(self):
        if self.user and self.user.role != EventCoreUser.ROLE_RESIDENT:
            raise ValidationError({'user': 'Only users with the Resident / Participant role can register.'})
        if self.registration_status == self.STATUS_WAITLISTED and not self.waitlist_position:
            raise ValidationError({'waitlist_position': 'Waitlisted participants need a waitlist position.'})
        if self.registration_status != self.STATUS_WAITLISTED and self.waitlist_position:
            raise ValidationError({'waitlist_position': 'Only waitlisted participants should have a waitlist position.'})


class Resource(models.Model):
    CATEGORY_EQUIPMENT = 'equipment'
    CATEGORY_SUPPLIES = 'supplies'
    CATEGORY_FOOD = 'food'
    CATEGORY_MEDICINE = 'medicine'
    CATEGORY_VENUE = 'venue'
    CATEGORY_OTHER = 'other'

    CATEGORY_CHOICES = [
        (CATEGORY_EQUIPMENT, 'Equipment'),
        (CATEGORY_SUPPLIES, 'Supplies'),
        (CATEGORY_FOOD, 'Food'),
        (CATEGORY_MEDICINE, 'Medicine'),
        (CATEGORY_VENUE, 'Venue'),
        (CATEGORY_OTHER, 'Other'),
    ]

    STATUS_REQUESTED = 'requested'
    STATUS_AVAILABLE = 'available'
    STATUS_USED = 'used'
    STATUS_RETURNED = 'returned'
    STATUS_DAMAGED = 'damaged'

    STATUS_CHOICES = [
        (STATUS_REQUESTED, 'Requested'),
        (STATUS_AVAILABLE, 'Available'),
        (STATUS_USED, 'Used'),
        (STATUS_RETURNED, 'Returned'),
        (STATUS_DAMAGED, 'Damaged'),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='resources')
    name = models.CharField(max_length=120)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default=CATEGORY_SUPPLIES)
    quantity = models.PositiveIntegerField(default=1)
    unit = models.CharField(max_length=30, default='pcs')
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    actual_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_REQUESTED)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'resources'
        ordering = ['event', 'name']
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name='resource_quantity_positive'),
            models.CheckConstraint(condition=models.Q(estimated_cost__gte=0), name='resource_estimated_cost_not_negative'),
            models.CheckConstraint(condition=models.Q(actual_cost__gte=0), name='resource_actual_cost_not_negative'),
        ]

    def __str__(self):
        return f'{self.name} ({self.quantity} {self.unit})'

    def clean(self):
        if self.quantity < 1:
            raise ValidationError({'quantity': 'Quantity must be at least 1.'})
        if self.estimated_cost < 0:
            raise ValidationError({'estimated_cost': 'Estimated cost cannot be negative.'})
        if self.actual_cost < 0:
            raise ValidationError({'actual_cost': 'Actual cost cannot be negative.'})


class Feedback(models.Model):
    RATING_CHOICES = [
        (1, '1 - Needs Improvement'),
        (2, '2 - Fair'),
        (3, '3 - Good'),
        (4, '4 - Very Good'),
        (5, '5 - Excellent'),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='feedback')
    participant = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='feedback_entries',
    )
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    comments = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'feedback'
        ordering = ['-submitted_at']
        constraints = [
            models.CheckConstraint(condition=models.Q(rating__gte=1) & models.Q(rating__lte=5), name='feedback_rating_1_to_5'),
        ]

    def __str__(self):
        return f'{self.event} feedback - {self.rating}/5'


class Notification(models.Model):
    recipient = models.ForeignKey(EventCoreUser, on_delete=models.CASCADE, related_name='notifications')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    title = models.CharField(max_length=120)
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} - {self.recipient}'
