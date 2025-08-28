# forms.py
from django import forms
from django.contrib.auth.models import User
from django.forms.widgets import DateInput, Select, Textarea
from datetime import date
import datetime
from .models import (
    Customer, Mortgage, InsurancePolicy, Application, 
    Communication, Document, Commission, Advisor,Payment,CommissionWeek,CommissionApplicationMapping,CommissionMapping
)

# forms.py
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
User = get_user_model()

class AdvisorCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'date_of_birth', 
                 'phone', 'license_number', 'specialization', 'hire_date', 'active',
                 'is_manager', 'notes')
        
class AdvisorForm(forms.ModelForm):
    # User model fields
    first_name = forms.CharField(
        max_length=150, 
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        max_length=150, 
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    username = forms.CharField(
        max_length=150, 
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}), 
        required=False
    )
    
    class Meta:
        model = User  # This should be your Advisor model (which is the User)
        fields = ['username', 'email', 'first_name', 'last_name', 'license_number', 
                 'specialization', 'phone', 'hire_date', 'active', 'date_of_birth',
                 'is_manager', 'notes']
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'license_number': forms.TextInput(attrs={'class': 'form-control'}),
            'specialization': forms.TextInput(attrs={'class': 'form-control'}),
            'hire_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_manager': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove the user field access since Advisor IS the user
        if self.instance and self.instance.pk:
            # Make username read-only when editing
            self.fields['username'].widget.attrs['readonly'] = True
    
    def save(self, commit=True):
        # Get the instance (which is the Advisor/User)
        advisor = super().save(commit=False)
        
        # Handle password if provided
        password = self.cleaned_data.get('password')
        if password:
            advisor.set_password(password)
        
        if commit:
            advisor.save()
        
        return advisor

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        exclude = ['customer_id', 'advisor', 'created_at', 'updated_at']  # Remove advisor from exclude
        widgets = {
            'date_of_birth': DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'alternate_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control'}),
            'address': Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'employment_status': Select(attrs={'class': 'form-control'}),
            'employer': forms.TextInput(attrs={'class': 'form-control'}),
            'job_title': forms.TextInput(attrs={'class': 'form-control'}),
            'annual_income': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'marital_status': Select(attrs={'class': 'form-control'}),
            'dependents': forms.NumberInput(attrs={'class': 'form-control'}),
            #'advisor': Select(attrs={'class': 'form-control'}),  # Add advisor widget
            'lead_source': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Make required fields more obvious
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['email'].required = True

class MortgageForm(forms.ModelForm):
    class Meta:
        model = Mortgage
        exclude = ['mortgage_id', 'advisor', 'created_at', 'updated_at']
        widgets = {
            'customer': Select(attrs={'class': 'form-control'}),
            'property_address': Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'property_city': forms.TextInput(attrs={'class': 'form-control'}),
            'property_state': forms.TextInput(attrs={'class': 'form-control'}),
            'property_postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'property_value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'loan_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'down_payment': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'interest_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'loan_term': forms.NumberInput(attrs={'class': 'form-control'}),
            'mortgage_type': Select(attrs={'class': 'form-control'}),
            'lender': forms.TextInput(attrs={'class': 'form-control'}),
            'loan_to_value_ratio': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'monthly_payment': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'property_type': Select(attrs={'class': 'form-control'}),
            'purpose': Select(attrs={'class': 'form-control'}),
            'mortgage_status': Select(attrs={'class': 'form-control'}),
            'application_date': DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'completion_date': DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'next_review_date': DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'broker_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'notes': Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

class InsurancePolicyForm(forms.ModelForm):
    class Meta:
        model = InsurancePolicy
        exclude = ['insurance_id', 'advisor', 'created_at', 'updated_at']
        widgets = {
            'customer': Select(attrs={'class': 'form-control'}),
            'policy_number': forms.TextInput(attrs={'class': 'form-control'}),
            'policy_type': Select(attrs={'class': 'form-control'}),
            'coverage_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'premium_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'premium_frequency': Select(attrs={'class': 'form-control'}),
            'insurance_company': forms.TextInput(attrs={'class': 'form-control'}),
            'policy_start_date': DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'policy_end_date': DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'renewal_date': DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'policy_status': Select(attrs={'class': 'form-control'}),
            'underwriting_class': forms.TextInput(attrs={'class': 'form-control'}),
            'beneficiary': forms.TextInput(attrs={'class': 'form-control'}),
            'commission_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'commission_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'next_review_date': DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'automatic_renewal': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

# forms.py - ApplicationForm

class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        exclude = ['application_id', 'advisor', 'created_at', 'updated_at', 'application_number']
        widgets = {
            'customer': Select(attrs={'class': 'form-control'}),
            'mortgage': Select(attrs={'class': 'form-control'}),
            'insurance': Select(attrs={'class': 'form-control'}),
            'solicitor_name': forms.TextInput(attrs={'class': 'form-control'}),
            'application_type': Select(attrs={'class': 'form-control'}),
            'application_status': Select(attrs={'class': 'form-control'}),
            'application_priority': Select(attrs={'class': 'form-control'}),
            'submitted_date': DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'expected_completion_date': DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'actual_completion_date': DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'decline_reason': Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'advisor_notes': Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'internal_notes': Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'follow_up_date': DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['mortgage'].required = False
        self.fields['insurance'].required = False
        self.fields['solicitor_name'].required = False
        self.fields['submitted_date'].required = False
        self.fields['expected_completion_date'].required = False
        self.fields['actual_completion_date'].required = False
        self.fields['decline_reason'].required = False
        self.fields['follow_up_date'].required = False
        self.fields['insurance_type'].required = False
        
        # Set required fields
        self.fields['customer'].required = True
        self.fields['application_type'].required = True

class CommunicationForm(forms.ModelForm):
    class Meta:
        model = Communication
        exclude = ['communication_id', 'customer', 'advisor', 'created_at']
        widgets = {
            'application': Select(attrs={'class': 'form-control'}),
            'communication_type': Select(attrs={'class': 'form-control'}),
            'direction': Select(attrs={'class': 'form-control'}),
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
            'content': Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'outcome': forms.TextInput(attrs={'class': 'form-control'}),
            'follow_up_required': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'follow_up_date': DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'communication_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['application'].required = False
        self.fields['application'].empty_label = "Select Application (if applicable)"

class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        exclude = ['document_id', 'application', 'customer', 'uploaded_by', 'created_at', 'updated_at']
        widgets = {
            'document_type': Select(attrs={'class': 'form-control'}),
            'document_name': forms.TextInput(attrs={'class': 'form-control'}),
            'file_path': forms.TextInput(attrs={'class': 'form-control'}),
            'document_status': Select(attrs={'class': 'form-control'}),
            'requested_date': DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'received_date': DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'expiry_date': DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notes': Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class ApplicationStatusUpdateForm(forms.Form):
    STATUS_CHOICES = Application.STATUS_CHOICES
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        widget=Select(attrs={'class': 'form-control'})
    )
    notes = forms.CharField(
        required=False,
        widget=Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Add notes about this status change...'})
    )

class CommissionForm(forms.ModelForm):
    class Meta:
        model = Commission
        exclude = ['commission_id', 'advisor', 'created_at']
        widgets = {
            'customer': Select(attrs={'class': 'form-control'}),
            'mortgage': Select(attrs={'class': 'form-control'}),
            'insurance': Select(attrs={'class': 'form-control'}),
            'commission_type': Select(attrs={'class': 'form-control'}),
            'gross_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'commission_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'commission_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'payment_status': Select(attrs={'class': 'form-control'}),
            'payment_date': DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'tax_year': forms.NumberInput(attrs={'class': 'form-control'}),
            'notes': Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['mortgage'].required = False
        self.fields['insurance'].required = False
        self.fields['mortgage'].empty_label = "Select Mortgage (if applicable)"
        self.fields['insurance'].empty_label = "Select Insurance (if applicable)"

class SearchForm(forms.Form):
    search = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search customers, applications, policies...'
        })
    )

class DateRangeForm(forms.Form):
    start_date = forms.DateField(
        widget=DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    end_date = forms.DateField(
        widget=DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

# Add to forms.py
class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        exclude = ['payment_id', 'created_at', 'updated_at']
        widgets = {
            'customer': Select(attrs={'class': 'form-control'}),
            'application': Select(attrs={'class': 'form-control'}),
            'mortgage': Select(attrs={'class': 'form-control'}),
            'insurance': Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'payment_method': Select(attrs={'class': 'form-control'}),
            'payment_status': Select(attrs={'class': 'form-control'}),
            'payment_date': DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class CommissionWeekForm(forms.ModelForm):
    class Meta:
        model = CommissionWeek
        fields = ['week_number', 'year', 'start_date', 'end_date', 'advisor', 'status', 'notes']
    
    def clean_week_number(self):
        week_number = self.cleaned_data['week_number']
        if week_number < 1 or week_number > 53:
            raise forms.ValidationError('Week number must be between 1 and 53')
        return week_number
    
    def clean_year(self):
        year = self.cleaned_data['year']
        current_year = date.today().year
        if year < current_year:
            raise forms.ValidationError('Cannot create commission weeks for past years')
        return year
    
    def clean(self):
        cleaned_data = super().clean()
        week_number = cleaned_data.get('week_number')
        year = cleaned_data.get('year')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if week_number and year and start_date and end_date:
            # Validate that dates match the week number
            expected_start = date.fromisocalendar(year, week_number, 1)
            expected_end = date.fromisocalendar(year, week_number, 7)
            
            if start_date != expected_start:
                self.add_error('start_date', f'Start date should be {expected_start} for week {week_number}')
            if end_date != expected_end:
                self.add_error('end_date', f'End date should be {expected_end} for week {week_number}')
        
        return cleaned_data

class CommissionApplicationMappingForm(forms.ModelForm):
    class Meta:
        model = CommissionApplicationMapping
        exclude = ['mapping_id', 'created_at', 'updated_at']
        widgets = {
            'application': Select(attrs={'class': 'form-control'}),
            'commission_week': Select(attrs={'class': 'form-control'}),
            'estimated_commission': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'actual_commission': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'commission_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'notes': Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class CommissionMappingForm(forms.ModelForm):
    class Meta:
        model = CommissionMapping
        fields = ['commission_rate', 'estimated_commission', 'actual_commission', 'notes']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        