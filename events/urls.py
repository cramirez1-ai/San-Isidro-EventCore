from django.contrib.auth import views as auth_views
from django.urls import path

from . import views


urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', auth_views.LoginView.as_view(template_name='events/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', views.register, name='register'),
    path(
        'forgot-password/',
        auth_views.PasswordResetView.as_view(
            template_name='events/password_reset_form.html',
            email_template_name='events/password_reset_email.html',
            subject_template_name='events/password_reset_subject.txt',
            success_url='/forgot-password/done/',
        ),
        name='password_reset',
    ),
    path(
        'forgot-password/done/',
        auth_views.PasswordResetDoneView.as_view(template_name='events/password_reset_done.html'),
        name='password_reset_done',
    ),
    path(
        'reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='events/password_reset_confirm.html',
            success_url='/reset/done/',
        ),
        name='password_reset_confirm',
    ),
    path(
        'reset/done/',
        auth_views.PasswordResetCompleteView.as_view(template_name='events/password_reset_complete.html'),
        name='password_reset_complete',
    ),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('events/', views.event_list, name='event_list'),
    path('events/add/', views.event_create, name='event_create'),
    path('events/<int:pk>/', views.event_detail, name='event_detail'),
    path('events/<int:pk>/edit/', views.event_update, name='event_update'),
    path('events/<int:pk>/delete/', views.event_delete, name='event_delete'),
    path('events/<int:pk>/organizers/add/', views.organizer_add, name='organizer_add'),
    path('organizers/<int:pk>/delete/', views.organizer_delete, name='organizer_delete'),
    path('events/<int:pk>/volunteers/add/', views.volunteer_add, name='volunteer_add'),
    path('volunteers/<int:pk>/attendance/', views.volunteer_attendance_update, name='volunteer_attendance_update'),
    path('volunteers/<int:pk>/delete/', views.volunteer_delete, name='volunteer_delete'),
    path('events/<int:pk>/participants/add/', views.participant_add, name='participant_add'),
    path('events/<int:pk>/participants/self-register/', views.participant_self_register, name='participant_self_register'),
    path('participants/<int:pk>/attendance/', views.participant_attendance_update, name='participant_attendance_update'),
    path('participants/<int:pk>/promote/', views.participant_promote, name='participant_promote'),
    path('participants/<int:pk>/delete/', views.participant_delete, name='participant_delete'),
    path('events/<int:pk>/resources/add/', views.resource_add, name='resource_add'),
    path('resources/<int:pk>/delete/', views.resource_delete, name='resource_delete'),
    path('events/<int:pk>/feedback/add/', views.feedback_add, name='feedback_add'),
    path('feedback/<int:pk>/delete/', views.feedback_delete, name='feedback_delete'),
    path('people/', views.people_list, name='people_list'),
    path('people/add/', views.person_create, name='person_create'),
    path('people/<int:pk>/edit/', views.person_update, name='person_update'),
    path('people/<int:pk>/delete/', views.person_delete, name='person_delete'),
    path('notifications/', views.notification_list, name='notification_list'),
    path('notifications/<int:pk>/read/', views.notification_mark_read, name='notification_mark_read'),
    path('notifications/read-all/', views.notification_mark_all_read, name='notification_mark_all_read'),
]
