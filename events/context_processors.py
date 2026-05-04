from .models import EventCoreUser


def eventcore_user_context(request):
    profile = None
    unread_notifications_count = 0

    if request.user.is_authenticated:
        try:
            profile = request.user.eventcore_profile
        except EventCoreUser.DoesNotExist:
            if request.user.is_superuser:
                profile, _ = EventCoreUser.objects.get_or_create(
                    auth_user=request.user,
                    defaults={
                        'first_name': request.user.first_name or request.user.username,
                        'last_name': request.user.last_name or 'Admin',
                        'email': request.user.email or f'{request.user.username}@eventcore.local',
                        'role': EventCoreUser.ROLE_ADMIN,
                    },
                )

        if profile:
            unread_notifications_count = profile.notifications.filter(is_read=False).count()

    return {
        'current_profile': profile,
        'unread_notifications_count': unread_notifications_count,
    }
