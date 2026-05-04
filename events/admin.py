from django.contrib import admin

from .models import (
    Event,
    EventCoreUser,
    EventOrganizer,
    Feedback,
    Notification,
    Participant,
    Resource,
    Volunteer,
)


@admin.register(EventCoreUser)
class EventCoreUserAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'role', 'email', 'contact_number', 'auth_user')
    list_filter = ('role',)
    search_fields = ('first_name', 'last_name', 'email', 'contact_number')


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'event_type',
        'location',
        'start_datetime',
        'end_datetime',
        'capacity',
        'budget',
        'status',
    )
    list_filter = ('event_type', 'status', 'start_datetime')
    search_fields = ('title', 'location', 'description')
    date_hierarchy = 'start_datetime'


@admin.register(EventOrganizer)
class EventOrganizerAdmin(admin.ModelAdmin):
    list_display = ('event', 'organizer', 'responsibility', 'assigned_at')
    list_filter = ('event',)
    search_fields = ('event__title', 'organizer__first_name', 'organizer__last_name', 'responsibility')


@admin.register(Volunteer)
class VolunteerAdmin(admin.ModelAdmin):
    list_display = ('event', 'user', 'task_assigned', 'attendance_status', 'registered_at')
    list_filter = ('attendance_status', 'event')
    search_fields = ('event__title', 'user__first_name', 'user__last_name', 'task_assigned')


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ('event', 'user', 'registration_status', 'waitlist_position', 'attendance_status', 'registered_at')
    list_filter = ('registration_status', 'attendance_status', 'event')
    search_fields = ('event__title', 'user__first_name', 'user__last_name')


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'event', 'category', 'quantity', 'unit', 'estimated_cost', 'actual_cost', 'status')
    list_filter = ('category', 'status', 'event')
    search_fields = ('name', 'event__title', 'notes')


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('event', 'participant', 'rating', 'submitted_at')
    list_filter = ('rating', 'event')
    search_fields = ('event__title', 'comments')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'recipient', 'event', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('title', 'message', 'recipient__first_name', 'recipient__last_name')
