from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    EventCoreUserForm,
    EventForm,
    EventOrganizerForm,
    FeedbackForm,
    ParticipantForm,
    RegisterForm,
    ResourceForm,
    VolunteerForm,
)
from .models import Event, EventCoreUser, EventOrganizer, Feedback, Notification, Participant, Resource, Volunteer


MANAGER_ROLES = (EventCoreUser.ROLE_ADMIN, EventCoreUser.ROLE_ORGANIZER)
ATTENDANCE_ROLES = (EventCoreUser.ROLE_ADMIN, EventCoreUser.ROLE_ORGANIZER, EventCoreUser.ROLE_VOLUNTEER)


def get_current_profile(user):
    if not user.is_authenticated:
        return None

    profile = EventCoreUser.objects.filter(auth_user=user).first()
    if profile:
        return profile

    if not user.is_superuser:
        return None

    email = user.email or f'{user.username}@eventcore.local'
    if EventCoreUser.objects.filter(email=email).exists():
        email = f'{user.username}-admin@eventcore.local'

    return EventCoreUser.objects.create(
        auth_user=user,
        first_name=user.first_name or user.username,
        last_name=user.last_name or 'Admin',
        email=email,
        role=EventCoreUser.ROLE_ADMIN,
    )


def user_has_role(user, *roles):
    if user.is_superuser:
        return True
    profile = get_current_profile(user)
    return bool(profile and profile.role in roles)


def role_required(*roles):
    def decorator(view_func):
        @login_required
        def wrapper(request, *args, **kwargs):
            if user_has_role(request.user, *roles):
                return view_func(request, *args, **kwargs)

            messages.error(request, 'You do not have permission to access that feature.')
            return redirect('dashboard')

        return wrapper

    return decorator


def create_notification(recipient, title, message, link='', event=None):
    if recipient:
        Notification.objects.create(
            recipient=recipient,
            title=title,
            message=message,
            link=link,
            event=event,
        )


def notify_roles(roles, title, message, link='', event=None, exclude_profile=None):
    recipients = EventCoreUser.objects.filter(role__in=roles)
    if exclude_profile:
        recipients = recipients.exclude(pk=exclude_profile.pk)

    Notification.objects.bulk_create(
        [
            Notification(
                recipient=recipient,
                title=title,
                message=message,
                link=link,
                event=event,
            )
            for recipient in recipients
        ]
    )


def set_participant_registration_status(participant):
    confirmed_count = Participant.objects.filter(
        event=participant.event,
        registration_status=Participant.STATUS_CONFIRMED,
    ).count()

    if confirmed_count < participant.event.capacity:
        participant.registration_status = Participant.STATUS_CONFIRMED
        participant.waitlist_position = None
        return 'confirmed'

    waitlist_count = Participant.objects.filter(
        event=participant.event,
        registration_status=Participant.STATUS_WAITLISTED,
    ).count()
    participant.registration_status = Participant.STATUS_WAITLISTED
    participant.waitlist_position = waitlist_count + 1
    return 'waitlisted'


def renumber_waitlist(event):
    waitlisted = Participant.objects.filter(
        event=event,
        registration_status=Participant.STATUS_WAITLISTED,
    ).order_by('waitlist_position', 'registered_at')

    for position, participant in enumerate(waitlisted, start=1):
        if participant.waitlist_position != position:
            participant.waitlist_position = position
            participant.save(update_fields=['waitlist_position'])


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            profile = user.eventcore_profile
            create_notification(
                profile,
                'Welcome to EventCore',
                'Your account was created successfully. You can now view events and use features for your role.',
                reverse('dashboard'),
            )
            login(request, user)
            messages.success(request, 'Registration successful. Welcome to EventCore!')
            return redirect('dashboard')
    else:
        form = RegisterForm()

    return render(request, 'events/register.html', {'form': form})


@login_required
def dashboard(request):
    profile = get_current_profile(request.user)
    now = timezone.now()

    total_budget = Event.objects.aggregate(total=Sum('budget'))['total'] or 0
    actual_resource_cost = Resource.objects.aggregate(total=Sum('actual_cost'))['total'] or 0
    average_rating = Feedback.objects.aggregate(avg=Avg('rating'))['avg']

    stats = {
        'total_events': Event.objects.count(),
        'upcoming_events': Event.objects.filter(start_datetime__gte=now).count(),
        'completed_events': Event.objects.filter(status=Event.STATUS_COMPLETED).count(),
        'total_people': EventCoreUser.objects.count(),
        'confirmed_participants': Participant.objects.filter(registration_status=Participant.STATUS_CONFIRMED).count(),
        'waitlisted_participants': Participant.objects.filter(registration_status=Participant.STATUS_WAITLISTED).count(),
        'resources': Resource.objects.count(),
        'total_budget': total_budget,
        'actual_resource_cost': actual_resource_cost,
        'average_rating': round(average_rating, 1) if average_rating else None,
    }

    context = {
        'stats': stats,
        'upcoming_events_list': Event.objects.filter(start_datetime__gte=now).order_by('start_datetime')[:5],
        'recent_feedback': Feedback.objects.select_related('event', 'participant__user')[:5],
        'recent_notifications': profile.notifications.all()[:5] if profile else [],
    }
    return render(request, 'events/dashboard.html', context)


@login_required
def event_list(request):
    events = Event.objects.prefetch_related(
        'organizer_assignments',
        'volunteers',
        'participants',
        'resources',
        'feedback',
    )

    query = request.GET.get('q', '').strip()
    event_type = request.GET.get('event_type', '').strip()
    status = request.GET.get('status', '').strip()

    if query:
        events = events.filter(
            Q(title__icontains=query)
            | Q(location__icontains=query)
            | Q(description__icontains=query)
        )
    if event_type:
        events = events.filter(event_type=event_type)
    if status:
        events = events.filter(status=status)

    context = {
        'events': events,
        'query': query,
        'selected_event_type': event_type,
        'selected_status': status,
        'event_type_choices': Event.EVENT_TYPE_CHOICES,
        'status_choices': Event.STATUS_CHOICES,
        'can_manage_events': user_has_role(request.user, *MANAGER_ROLES),
    }
    return render(request, 'events/event_list.html', context)


@login_required
def event_detail(request, pk):
    event = get_object_or_404(
        Event.objects.prefetch_related(
            'organizer_assignments__organizer',
            'volunteers__user',
            'participants__user',
            'resources',
            'feedback__participant__user',
        ),
        pk=pk,
    )
    profile = get_current_profile(request.user)
    current_participant = (
        Participant.objects.filter(event=event, user=profile).first()
        if profile and profile.role == EventCoreUser.ROLE_RESIDENT
        else None
    )

    context = {
        'event': event,
        'organizer_form': EventOrganizerForm(),
        'volunteer_form': VolunteerForm(),
        'participant_form': ParticipantForm(),
        'resource_form': ResourceForm(),
        'feedback_form': FeedbackForm(event=event),
        'volunteer_attendance_choices': Volunteer.ATTENDANCE_CHOICES,
        'participant_attendance_choices': Participant.ATTENDANCE_CHOICES,
        'can_manage_event': user_has_role(request.user, *MANAGER_ROLES),
        'can_track_attendance': user_has_role(request.user, *ATTENDANCE_ROLES),
        'current_participant': current_participant,
        'can_self_register': bool(
            profile
            and profile.role == EventCoreUser.ROLE_RESIDENT
            and not current_participant
            and event.status != Event.STATUS_CANCELLED
        ),
    }
    return render(request, 'events/event_detail.html', context)


@role_required(*MANAGER_ROLES)
def event_create(request):
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save()
            actor = get_current_profile(request.user)
            notify_roles(
                MANAGER_ROLES,
                'New event created',
                f'"{event.title}" has been added to EventCore.',
                reverse('event_detail', args=[event.pk]),
                event=event,
                exclude_profile=actor,
            )
            messages.success(request, f'"{event.title}" was added successfully.')
            return redirect('event_detail', pk=event.pk)
    else:
        form = EventForm()

    return render(request, 'events/event_form.html', {'form': form, 'page_title': 'Add Event'})


@role_required(*MANAGER_ROLES)
def event_update(request, pk):
    event = get_object_or_404(Event, pk=pk)

    if request.method == 'POST':
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            event = form.save()
            messages.success(request, f'"{event.title}" was updated successfully.')
            return redirect('event_detail', pk=event.pk)
    else:
        form = EventForm(instance=event)

    return render(
        request,
        'events/event_form.html',
        {'form': form, 'event': event, 'page_title': 'Update Event'},
    )


@role_required(*MANAGER_ROLES)
def event_delete(request, pk):
    event = get_object_or_404(Event, pk=pk)

    if request.method == 'POST':
        title = event.title
        event.delete()
        messages.success(request, f'"{title}" was deleted successfully.')
        return redirect('event_list')

    return render(request, 'events/event_confirm_delete.html', {'event': event})


@role_required(EventCoreUser.ROLE_ADMIN)
def people_list(request):
    users = EventCoreUser.objects.select_related('auth_user')
    role_cards = [
        ('Admin', users.filter(role=EventCoreUser.ROLE_ADMIN).count()),
        ('Organizers', users.filter(role=EventCoreUser.ROLE_ORGANIZER).count()),
        ('Volunteers', users.filter(role=EventCoreUser.ROLE_VOLUNTEER).count()),
        ('Residents / Participants', users.filter(role=EventCoreUser.ROLE_RESIDENT).count()),
    ]
    return render(request, 'events/people_list.html', {'users': users, 'role_cards': role_cards})


@role_required(EventCoreUser.ROLE_ADMIN)
def person_create(request):
    if request.method == 'POST':
        form = EventCoreUserForm(request.POST)
        if form.is_valid():
            profile = form.save()
            create_notification(
                profile,
                'Profile created',
                'Your EventCore profile has been created by an administrator.',
                reverse('dashboard'),
            )
            messages.success(request, f'{profile.first_name} {profile.last_name} was added successfully.')
            return redirect('people_list')
    else:
        form = EventCoreUserForm()

    return render(request, 'events/person_form.html', {'form': form, 'page_title': 'Add Person'})


@role_required(EventCoreUser.ROLE_ADMIN)
def person_update(request, pk):
    profile = get_object_or_404(EventCoreUser, pk=pk)

    if request.method == 'POST':
        form = EventCoreUserForm(request.POST, instance=profile)
        if form.is_valid():
            profile = form.save()
            if profile.auth_user:
                profile.auth_user.first_name = profile.first_name
                profile.auth_user.last_name = profile.last_name
                profile.auth_user.email = profile.email
                profile.auth_user.is_staff = profile.role == EventCoreUser.ROLE_ADMIN
                profile.auth_user.save(update_fields=['first_name', 'last_name', 'email', 'is_staff'])
            messages.success(request, f'{profile.first_name} {profile.last_name} was updated successfully.')
            return redirect('people_list')
    else:
        form = EventCoreUserForm(instance=profile)

    return render(request, 'events/person_form.html', {'form': form, 'page_title': 'Update Person', 'person': profile})


@role_required(EventCoreUser.ROLE_ADMIN)
def person_delete(request, pk):
    profile = get_object_or_404(EventCoreUser, pk=pk)

    if request.method == 'POST':
        name = f'{profile.first_name} {profile.last_name}'
        auth_user = profile.auth_user
        profile.delete()
        if auth_user and not auth_user.is_superuser:
            auth_user.delete()
        messages.success(request, f'{name} was deleted successfully.')
        return redirect('people_list')

    return render(request, 'events/person_confirm_delete.html', {'person': profile})


def _redirect_with_form_errors(request, form, event, section_name):
    error_list = []
    for field, errors in form.errors.items():
        label = form.fields[field].label if field in form.fields else 'Form'
        error_list.append(f'{label}: {", ".join(errors)}')

    messages.error(request, f'Could not save {section_name}. {" ".join(error_list)}')
    return redirect('event_detail', pk=event.pk)


def _already_exists_error(request, event, message):
    messages.warning(request, message)
    return redirect('event_detail', pk=event.pk)


@require_POST
@role_required(*MANAGER_ROLES)
def organizer_add(request, pk):
    event = get_object_or_404(Event, pk=pk)
    form = EventOrganizerForm(request.POST)

    if form.is_valid():
        organizer = form.cleaned_data['organizer']
        if EventOrganizer.objects.filter(event=event, organizer=organizer).exists():
            return _already_exists_error(request, event, f'{organizer} is already assigned to this event.')

        assignment = form.save(commit=False)
        assignment.event = event
        assignment.save()
        create_notification(
            organizer,
            'Organizer assignment',
            f'You were assigned as an organizer for "{event.title}".',
            reverse('event_detail', args=[event.pk]),
            event=event,
        )
        messages.success(request, f'{organizer} was assigned as an organizer.')
        return redirect('event_detail', pk=event.pk)

    return _redirect_with_form_errors(request, form, event, 'organizer assignment')


@require_POST
@role_required(*MANAGER_ROLES)
def organizer_delete(request, pk):
    assignment = get_object_or_404(EventOrganizer, pk=pk)
    event_pk = assignment.event.pk
    organizer = assignment.organizer
    assignment.delete()
    messages.success(request, f'{organizer} was removed from the organizers.')
    return redirect('event_detail', pk=event_pk)


@require_POST
@role_required(*MANAGER_ROLES)
def volunteer_add(request, pk):
    event = get_object_or_404(Event, pk=pk)
    form = VolunteerForm(request.POST)

    if form.is_valid():
        volunteer_user = form.cleaned_data['user']
        if Volunteer.objects.filter(event=event, user=volunteer_user).exists():
            return _already_exists_error(request, event, f'{volunteer_user} is already assigned as a volunteer.')

        volunteer = form.save(commit=False)
        volunteer.event = event
        volunteer.save()
        create_notification(
            volunteer_user,
            'Volunteer assignment',
            f'You were assigned as a volunteer for "{event.title}".',
            reverse('event_detail', args=[event.pk]),
            event=event,
        )
        messages.success(request, f'{volunteer_user} was assigned as a volunteer.')
        return redirect('event_detail', pk=event.pk)

    return _redirect_with_form_errors(request, form, event, 'volunteer assignment')


@require_POST
@role_required(*ATTENDANCE_ROLES)
def volunteer_attendance_update(request, pk):
    volunteer = get_object_or_404(Volunteer, pk=pk)
    status = request.POST.get('attendance_status')
    valid_statuses = dict(Volunteer.ATTENDANCE_CHOICES)

    if status in valid_statuses:
        volunteer.attendance_status = status
        volunteer.save(update_fields=['attendance_status'])
        create_notification(
            volunteer.user,
            'Volunteer attendance updated',
            f'Your attendance for "{volunteer.event.title}" is now {valid_statuses[status]}.',
            reverse('event_detail', args=[volunteer.event.pk]),
            event=volunteer.event,
        )
        messages.success(request, f'Volunteer attendance updated to {valid_statuses[status]}.')
    else:
        messages.error(request, 'Invalid volunteer attendance status.')

    return redirect('event_detail', pk=volunteer.event.pk)


@require_POST
@role_required(*MANAGER_ROLES)
def volunteer_delete(request, pk):
    volunteer = get_object_or_404(Volunteer, pk=pk)
    event_pk = volunteer.event.pk
    volunteer_user = volunteer.user
    volunteer.delete()
    messages.success(request, f'{volunteer_user} was removed from the volunteers.')
    return redirect('event_detail', pk=event_pk)


@require_POST
@role_required(*MANAGER_ROLES)
def participant_add(request, pk):
    event = get_object_or_404(Event, pk=pk)
    form = ParticipantForm(request.POST)

    if form.is_valid():
        participant_user = form.cleaned_data['user']
        if Participant.objects.filter(event=event, user=participant_user).exists():
            return _already_exists_error(request, event, f'{participant_user} is already registered.')

        participant = form.save(commit=False)
        participant.event = event
        registration_status = set_participant_registration_status(participant)
        participant.save()

        create_notification(
            participant_user,
            'Event registration',
            f'You were {registration_status} for "{event.title}".',
            reverse('event_detail', args=[event.pk]),
            event=event,
        )
        if registration_status == 'waitlisted':
            messages.warning(request, f'{participant_user} was added to the waitlist because the event is full.')
        else:
            messages.success(request, f'{participant_user} was registered as a participant.')
        return redirect('event_detail', pk=event.pk)

    return _redirect_with_form_errors(request, form, event, 'participant registration')


@require_POST
@role_required(EventCoreUser.ROLE_RESIDENT)
def participant_self_register(request, pk):
    event = get_object_or_404(Event, pk=pk)
    profile = get_current_profile(request.user)

    if event.status == Event.STATUS_CANCELLED:
        messages.error(request, 'This event is cancelled and cannot accept registrations.')
        return redirect('event_detail', pk=event.pk)

    if Participant.objects.filter(event=event, user=profile).exists():
        messages.warning(request, 'You are already registered for this event.')
        return redirect('event_detail', pk=event.pk)

    participant = Participant(event=event, user=profile)
    registration_status = set_participant_registration_status(participant)
    participant.save()
    create_notification(
        profile,
        'Event registration',
        f'You were {registration_status} for "{event.title}".',
        reverse('event_detail', args=[event.pk]),
        event=event,
    )

    if registration_status == 'waitlisted':
        messages.warning(request, 'The event is full, so you were added to the waitlist.')
    else:
        messages.success(request, 'You are now registered for this event.')
    return redirect('event_detail', pk=event.pk)


@require_POST
@role_required(*ATTENDANCE_ROLES)
def participant_attendance_update(request, pk):
    participant = get_object_or_404(Participant, pk=pk)
    status = request.POST.get('attendance_status')
    valid_statuses = dict(Participant.ATTENDANCE_CHOICES)

    if status in valid_statuses:
        participant.attendance_status = status
        participant.save(update_fields=['attendance_status'])
        create_notification(
            participant.user,
            'Attendance updated',
            f'Your attendance for "{participant.event.title}" is now {valid_statuses[status]}.',
            reverse('event_detail', args=[participant.event.pk]),
            event=participant.event,
        )
        messages.success(request, f'Participant attendance updated to {valid_statuses[status]}.')
    else:
        messages.error(request, 'Invalid participant attendance status.')

    return redirect('event_detail', pk=participant.event.pk)


@require_POST
@role_required(*MANAGER_ROLES)
def participant_promote(request, pk):
    participant = get_object_or_404(Participant, pk=pk, registration_status=Participant.STATUS_WAITLISTED)
    event = participant.event

    if event.available_slots < 1:
        messages.error(request, 'No available slots yet. Increase capacity or remove a confirmed participant first.')
        return redirect('event_detail', pk=event.pk)

    participant.registration_status = Participant.STATUS_CONFIRMED
    participant.waitlist_position = None
    participant.save(update_fields=['registration_status', 'waitlist_position'])
    renumber_waitlist(event)
    create_notification(
        participant.user,
        'Waitlist update',
        f'You have been promoted from the waitlist for "{event.title}".',
        reverse('event_detail', args=[event.pk]),
        event=event,
    )
    messages.success(request, f'{participant.user} was promoted from the waitlist.')
    return redirect('event_detail', pk=event.pk)


@require_POST
@role_required(*MANAGER_ROLES)
def participant_delete(request, pk):
    participant = get_object_or_404(Participant, pk=pk)
    event = participant.event
    participant_user = participant.user
    participant.delete()
    renumber_waitlist(event)
    messages.success(request, f'{participant_user} was removed from the participants.')
    return redirect('event_detail', pk=event.pk)


@require_POST
@role_required(*MANAGER_ROLES)
def resource_add(request, pk):
    event = get_object_or_404(Event, pk=pk)
    form = ResourceForm(request.POST)

    if form.is_valid():
        resource = form.save(commit=False)
        resource.event = event
        resource.save()
        messages.success(request, f'{resource.name} was added to event resources.')
        return redirect('event_detail', pk=event.pk)

    return _redirect_with_form_errors(request, form, event, 'resource')


@require_POST
@role_required(*MANAGER_ROLES)
def resource_delete(request, pk):
    resource = get_object_or_404(Resource, pk=pk)
    event_pk = resource.event.pk
    resource_name = resource.name
    resource.delete()
    messages.success(request, f'{resource_name} was removed from resources.')
    return redirect('event_detail', pk=event_pk)


@require_POST
@login_required
def feedback_add(request, pk):
    event = get_object_or_404(Event, pk=pk)
    profile = get_current_profile(request.user)
    form = FeedbackForm(request.POST, event=event)

    if form.is_valid():
        feedback = form.save(commit=False)
        feedback.event = event

        if profile and profile.role == EventCoreUser.ROLE_RESIDENT:
            participant = Participant.objects.filter(
                event=event,
                user=profile,
                registration_status=Participant.STATUS_CONFIRMED,
            ).first()
            if not participant:
                messages.error(request, 'Only confirmed participants can submit feedback for this event.')
                return redirect('event_detail', pk=event.pk)
            feedback.participant = participant

        feedback.save()
        messages.success(request, 'Feedback was recorded successfully.')
        return redirect('event_detail', pk=event.pk)

    return _redirect_with_form_errors(request, form, event, 'feedback')


@require_POST
@role_required(*MANAGER_ROLES)
def feedback_delete(request, pk):
    feedback = get_object_or_404(Feedback, pk=pk)
    event_pk = feedback.event.pk
    feedback.delete()
    messages.success(request, 'Feedback was removed.')
    return redirect('event_detail', pk=event_pk)


@login_required
def notification_list(request):
    profile = get_current_profile(request.user)
    notifications = profile.notifications.all() if profile else []
    return render(request, 'events/notification_list.html', {'notifications': notifications})


@require_POST
@login_required
def notification_mark_read(request, pk):
    profile = get_current_profile(request.user)
    notification = get_object_or_404(Notification, pk=pk, recipient=profile)
    notification.is_read = True
    notification.save(update_fields=['is_read'])
    return redirect(notification.link or 'notification_list')


@require_POST
@login_required
def notification_mark_all_read(request):
    profile = get_current_profile(request.user)
    if profile:
        profile.notifications.filter(is_read=False).update(is_read=True)
    messages.success(request, 'All notifications were marked as read.')
    return redirect('notification_list')
