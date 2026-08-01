from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .ml_utils import get_dataset_options
from .models import CounsellingSession, CounsellorProfile, PaymentTransaction


FORM_CONTROL = {'class': 'form-control'}
FORM_SELECT = {'class': 'form-select'}


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs=FORM_CONTROL))
    full_name = forms.CharField(max_length=120, required=True, widget=forms.TextInput(attrs=FORM_CONTROL))

    class Meta:
        model = User
        fields = ['username', 'full_name', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ['username', 'password1', 'password2']:
            self.fields[name].widget.attrs.update(FORM_CONTROL)


class PredictionForm(forms.Form):
    exam = forms.ChoiceField(label='Exam', widget=forms.Select(attrs=FORM_SELECT))
    percentile = forms.FloatField(
        min_value=0,
        max_value=100,
        label='Exam Percentile',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Example: 88.50'})
    )
    rank = forms.IntegerField(
        min_value=0,
        required=False,
        label='Exam Rank',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Example: 25000'})
    )
    category = forms.ChoiceField(label='Category', widget=forms.Select(attrs=FORM_SELECT))
    home_region = forms.ChoiceField(label='Home Region / University', required=False, widget=forms.Select(attrs=FORM_SELECT))
    university_quota = forms.ChoiceField(label='University Quota', required=False, widget=forms.Select(attrs=FORM_SELECT))
    branch = forms.ChoiceField(label='Preferred Branch', widget=forms.Select(attrs=FORM_SELECT))
    round_name = forms.ChoiceField(label='CAP Round', widget=forms.Select(attrs=FORM_SELECT))
    city = forms.ChoiceField(label='Location Preference', required=False, widget=forms.Select(attrs=FORM_SELECT))
    college_type = forms.ChoiceField(label='College Type', required=False, widget=forms.Select(attrs=FORM_SELECT))
    max_fees = forms.IntegerField(
        min_value=0,
        required=False,
        label='Maximum Fees / Year',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Example: 150000'})
    )
    min_naac_score = forms.FloatField(
        min_value=0,
        max_value=4,
        required=False,
        label='Minimum NAAC Score',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Example: 3.0'})
    )
    max_nirf_rank = forms.IntegerField(
        min_value=0,
        required=False,
        label='Maximum NIRF Rank',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Example: 500'})
    )
    aptitude_score = forms.IntegerField(
        min_value=0,
        max_value=100,
        required=False,
        label='Aptitude Test Score',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Example: 75'})
    )
    top_n = forms.IntegerField(
        min_value=5,
        max_value=100,
        initial=30,
        label='Number of Recommendations',
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        opts = get_dataset_options()
        self.fields['exam'].choices = [(x, x) for x in opts['exams']]
        self.fields['category'].choices = [(x, x) for x in opts['categories']]
        self.fields['home_region'].choices = [('', 'Any Home Region')] + [(x, x) for x in opts['home_regions']]
        self.fields['university_quota'].choices = [('', 'Any Quota')] + [(x, x) for x in opts['university_quotas']]
        self.fields['branch'].choices = [(x, x) for x in opts['branches']]
        self.fields['round_name'].choices = [(x, x) for x in opts['rounds']]
        self.fields['city'].choices = [('', 'Any City')] + [(x, x) for x in opts['cities']]
        self.fields['college_type'].choices = [('', 'Any Type')] + [(x, x) for x in opts['college_types']]


class ChatbotForm(forms.Form):
    question = forms.CharField(
        label='Ask AI Counsellor',
        widget=forms.Textarea(attrs={
            'class': 'form-control chatbot-input',
            'rows': 3,
            'placeholder': 'Example: Given my JEE percentile, which Pune colleges are safe for Computer Engineering?',
        })
    )


class CounsellingBookingForm(forms.ModelForm):
    counsellor = forms.ModelChoiceField(
        queryset=CounsellorProfile.objects.filter(is_active=True),
        required=False,
        empty_label='Select counsellor or leave for auto-allocation',
        widget=forms.Select(attrs=FORM_SELECT)
    )

    class Meta:
        model = CounsellingSession
        fields = ['counsellor', 'student_name', 'email', 'phone', 'preferred_date', 'preferred_time', 'mode', 'topic']
        widgets = {
            'student_name': forms.TextInput(attrs={**FORM_CONTROL, 'placeholder': 'Student full name'}),
            'email': forms.EmailInput(attrs={**FORM_CONTROL, 'placeholder': 'Email address'}),
            'phone': forms.TextInput(attrs={**FORM_CONTROL, 'placeholder': 'Mobile number'}),
            'preferred_date': forms.DateInput(attrs={**FORM_CONTROL, 'type': 'date'}),
            'preferred_time': forms.TimeInput(attrs={**FORM_CONTROL, 'type': 'time'}),
            'mode': forms.Select(attrs=FORM_SELECT),
            'topic': forms.TextInput(attrs={**FORM_CONTROL, 'placeholder': 'Example: CAP round option form counselling'}),
        }

    def __init__(self, *args, **kwargs):
        counsellor_id = kwargs.pop('counsellor_id', None)
        super().__init__(*args, **kwargs)
        self.fields['counsellor'].queryset = CounsellorProfile.objects.filter(is_active=True)
        if counsellor_id:
            self.fields['counsellor'].initial = counsellor_id


class PaymentForm(forms.Form):
    payment_method = forms.ChoiceField(
        choices=[
            ('Demo UPI', 'Demo UPI'),
            ('Demo Card', 'Demo Card'),
            ('Demo Net Banking', 'Demo Net Banking'),
        ],
        widget=forms.Select(attrs=FORM_SELECT)
    )
    payer_name = forms.CharField(max_length=120, widget=forms.TextInput(attrs={**FORM_CONTROL, 'placeholder': 'Name on payment'}))
    confirm = forms.BooleanField(label='I confirm demo payment for this counselling session')


class CounsellorFilterForm(forms.Form):
    city = forms.CharField(required=False, widget=forms.TextInput(attrs={**FORM_CONTROL, 'placeholder': 'Mumbai / Pune'}))
    specialization = forms.CharField(required=False, widget=forms.TextInput(attrs={**FORM_CONTROL, 'placeholder': 'Engineering / CAP / Career'}))


class AptitudeAnswerForm(forms.Form):
    """Dynamic RIASEC aptitude form. The view passes active questions."""
    def __init__(self, *args, questions=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.questions = questions or []
        for q in self.questions:
            self.fields[f'q_{q.id}'] = forms.ChoiceField(
                label=q.question_text,
                choices=[
                    ('1', 'Strongly Disagree'),
                    ('2', 'Disagree'),
                    ('3', 'Neutral'),
                    ('4', 'Agree'),
                    ('5', 'Strongly Agree'),
                ],
                widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
                initial='3',
            )
