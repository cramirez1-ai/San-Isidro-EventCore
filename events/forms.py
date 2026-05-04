from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Event, EventCoreUser, EventOrganizer, Feedback, Participant, Resource, Volunteer


class RegisterForm(UserCreationForm):
    role = forms.ChoiceField(
        choices=[
            (EventCoreUser.ROLE_RESIDENT, 'Resident / Participant'),
            (EventCoreUser.ROLE_VOLUNTEER, 'Volunteer'),
            (EventCoreUser.ROLE_ORGANIZER, 'Barangay Organizer'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='Public registration does not create admin accounts. Create admins through createsuperuser/admin.',
    )
    first_name = forms.CharField(max_length=80, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=80, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    contact_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '09XXXXXXXXX'}),
    )
    address = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Purok / Street / Barangay'}),
    )

    class Meta:
        model = User
        fields = [
            'username',
            'first_name',
            'last_name',
            'email',
            'contact_number',
            'address',
            'role',
            'password1',
            'password2',
        ]
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})

    def clean_email(self):
        email = self.cleaned_data['email']
        if EventCoreUser.objects.filter(email=email).exists() or User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']

        if commit:
            user.save()
            EventCoreUser.objects.create(
                auth_user=user,
                first_name=user.first_name,
                last_name=user.last_name,
                email=user.email,
                contact_number=self.cleaned_data.get('contact_number', ''),
                address=self.cleaned_data.get('address', ''),
                role=self.cleaned_data['role'],
            )

        return user


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            'title',
            'event_type',
            'description',
            'location',
            'start_datetime',
            'end_datetime',
            'capacity',
            'budget',
            'status',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Example: Clean-up Drive'}),
            'event_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Describe the event objectives, target residents, and activity plan.',
                }
            ),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Example: Barangay Hall'}),
            'start_datetime': forms.DateTimeInput(
                format='%Y-%m-%dT%H:%M',
                attrs={'class': 'form-control', 'type': 'datetime-local'},
            ),
            'end_datetime': forms.DateTimeInput(
                format='%Y-%m-%dT%H:%M',
                attrs={'class': 'form-control', 'type': 'datetime-local'},
            ),
            'capacity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'budget': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['start_datetime'].input_formats = ['%Y-%m-%dT%H:%M']
        self.fields['end_datetime'].input_formats = ['%Y-%m-%dT%H:%M']

    def clean(self):
        cleaned_data = super().clean()
        start_datetime = cleaned_data.get('start_datetime')
        end_datetime = cleaned_data.get('end_datetime')

        if start_datetime and end_datetime and end_datetime <= start_datetime:
            self.add_error('end_datetime', 'End date and time must be later than the start date and time.')
        if cleaned_data.get('capacity') is not None and cleaned_data['capacity'] < 1:
            self.add_error('capacity', 'Capacity must be at least 1.')
        if cleaned_data.get('budget') is not None and cleaned_data['budget'] < 0:
            self.add_error('budget', 'Budget cannot be negative.')

        return cleaned_data


class EventCoreUserForm(forms.ModelForm):
    create_login_account = forms.BooleanField(
        required=False,
        label='Create Django login account',
        help_text='Useful when this person should be able to log in to EventCore.',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )
    username = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Leave blank to use email prefix'}),
    )
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Only needed for new login accounts'}),
    )

    class Meta:
        model = EventCoreUser
        fields = ['first_name', 'last_name', 'email', 'contact_number', 'address', 'role']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Example: Ana'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Example: Santos'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'example@email.com'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '09XXXXXXXXX'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Purok / Street / Barangay'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        create_login = cleaned_data.get('create_login_account')
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')

        if self.instance and self.instance.pk and self.instance.auth_user:
            return cleaned_data

        if create_login:
            if not password:
                self.add_error('password', 'Password is required when creating a login account.')
            if username and User.objects.filter(username=username).exists():
                self.add_error('username', 'This username is already taken.')

        return cleaned_data

    def save(self, commit=True):
        profile = super().save(commit=False)

        if commit:
            profile.save()

            if self.cleaned_data.get('create_login_account') and not profile.auth_user:
                username = self.cleaned_data.get('username') or profile.email.split('@')[0]
                if User.objects.filter(username=username).exists():
                    username = f'{username}{profile.pk}'

                auth_user = User.objects.create_user(
                    username=username,
                    email=profile.email,
                    password=self.cleaned_data['password'],
                    first_name=profile.first_name,
                    last_name=profile.last_name,
                    is_staff=profile.role == EventCoreUser.ROLE_ADMIN,
                )
                profile.auth_user = auth_user
                profile.save(update_fields=['auth_user'])

        return profile


class EventOrganizerForm(forms.ModelForm):
    class Meta:
        model = EventOrganizer
        fields = ['organizer', 'responsibility']
        widgets = {
            'organizer': forms.Select(attrs={'class': 'form-select'}),
            'responsibility': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Example: Program coordinator'}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['organizer'].queryset = EventCoreUser.objects.filter(role=EventCoreUser.ROLE_ORGANIZER)
        self.fields['organizer'].empty_label = 'Select barangay organizer'


class VolunteerForm(forms.ModelForm):
    class Meta:
        model = Volunteer
        fields = ['user', 'task_assigned', 'attendance_status']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-select'}),
            'task_assigned': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Example: Registration desk'}
            ),
            'attendance_status': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'user': 'Volunteer',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].queryset = EventCoreUser.objects.filter(role=EventCoreUser.ROLE_VOLUNTEER)
        self.fields['user'].empty_label = 'Select volunteer'


class ParticipantForm(forms.ModelForm):
    class Meta:
        model = Participant
        fields = ['user', 'attendance_status']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-select'}),
            'attendance_status': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'user': 'Resident / Participant',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].queryset = EventCoreUser.objects.filter(role=EventCoreUser.ROLE_RESIDENT)
        self.fields['user'].empty_label = 'Select resident / participant'


class ResourceForm(forms.ModelForm):
    class Meta:
        model = Resource
        fields = ['name', 'category', 'quantity', 'unit', 'estimated_cost', 'actual_cost', 'status', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Example: Plastic chairs'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'unit': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'pcs, boxes, packs'}),
            'estimated_cost': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'actual_cost': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('quantity') is not None and cleaned_data['quantity'] < 1:
            self.add_error('quantity', 'Quantity must be at least 1.')
        if cleaned_data.get('estimated_cost') is not None and cleaned_data['estimated_cost'] < 0:
            self.add_error('estimated_cost', 'Estimated cost cannot be negative.')
        if cleaned_data.get('actual_cost') is not None and cleaned_data['actual_cost'] < 0:
            self.add_error('actual_cost', 'Actual cost cannot be negative.')
        return cleaned_data


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['participant', 'rating', 'comments']
        widgets = {
            'participant': forms.Select(attrs={'class': 'form-select'}),
            'rating': forms.Select(attrs={'class': 'form-select'}),
            'comments': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'What went well? What can improve?'}
            ),
        }

    def __init__(self, *args, **kwargs):
        event = kwargs.pop('event', None)
        super().__init__(*args, **kwargs)
        if event:
            self.fields['participant'].queryset = Participant.objects.filter(event=event).select_related('user')
        self.fields['participant'].required = False
        self.fields['participant'].empty_label = 'Anonymous / no participant selected'
