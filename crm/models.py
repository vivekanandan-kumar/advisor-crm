# models.py
from django.contrib.auth import get_user_model
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.urls import reverse
from django.utils import timezone
import json
from django.conf import settings
import uuid
from datetime import datetime

def generate_mortgage_id():
    now = datetime.now()
    timestamp = now.strftime('%Y%m%d%H%M%S')
    # Use a part of a UUID for extra uniqueness
    unique_part = str(uuid.uuid4())[:6]
    return f"MRT_{timestamp}_{unique_part}"

def generate_insurance_id():
    now = datetime.now()
    timestamp = now.strftime('%Y%m%d%H%M%S')
    # Use a part of a UUID for extra uniqueness
    unique_part = str(uuid.uuid4())[:6]
    return f"INS_{timestamp}_{unique_part}"

# Add a new function for application number generation using initial
def generate_application_number(advisor, application_type, insurance_type=None):
    """Generate application number using advisor initial with sequential counter"""
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')

    # Create insurance type abbreviation mapping
    insurance_abbreviations = {
        'Life Insurance': 'LIFE',
        'Critical Illness': 'CI',
        'Income Protection': 'IP',
        'Buildings Insurance': 'BLDG',
        'Contents Insurance': 'CNT',
        'Motor Insurance': 'MOTOR',
        'Travel Insurance': 'TRVL',
        'Mortgage': 'MORT',
        'Both': 'COMB'
    }

    # Determine the base pattern based on application type
    if application_type == 'Insurance' and insurance_type:
        prefix = insurance_abbreviations.get(insurance_type, 'INS')
        base_pattern = f"APP_INS_{prefix}_{advisor.initial}_{timestamp}"
    elif application_type == 'Mortgage':
        base_pattern = f"APP_MORT_{advisor.initial}_{timestamp}"
    elif application_type == 'Both':
        base_pattern = f"APP_BOTH_{advisor.initial}_{timestamp}"
    else:
        base_pattern = f"APP_{advisor.initial}_{timestamp}"

    # Count existing applications with the same base pattern
    existing_count = Application.objects.filter(
        application_number__startswith=base_pattern
    ).count()

    return f"{base_pattern}_{existing_count +1:03d}"

# models.py - Update Advisor model
class Advisor(AbstractUser):
    # Custom fields matching your SQL table
    date_of_birth = models.DateField(null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    license_number = models.CharField(max_length=50, unique=True, null=True, blank=True)
    specialization = models.CharField(
        max_length=100,
        blank=True,
        help_text='e.g., Mortgages, Life Insurance, Property Insurance'
    )
    hire_date = models.DateField(default=timezone.now)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_manager = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)
    # Override email field to make it unique and required
    email = models.EmailField(unique=True, blank=False)

    # Override first_name and last_name to make them required
    first_name = models.CharField(max_length=50, blank=False)
    last_name = models.CharField(max_length=50, blank=False)

    # Add profile image field
    profile_image = models.ImageField(
        upload_to='profile_images/advisor_profiles/%Y/%m/%d/',
        null=True,
        blank=True,
        default='advisor_profiles/default.png'
    )

    # Add initial field for 2-character short name
    initial = models.CharField(
        max_length=3,
        unique=True,
        blank=True,
        null=True,
        help_text='2-character unique initial (e.g., JD for John Doe)'
    )

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def save(self, *args, **kwargs):
        # Generate initial from first and last name if not provided
        if not self.initial:
            self.initial = self.generate_initial()
        super().save(*args, **kwargs)

    def generate_initial(self):
        """Generate 2-character initial from first and last name"""
        if self.first_name and self.last_name:
            return (self.first_name[0] + self.last_name[0]).upper()
        elif self.first_name:
            return self.first_name[:2].upper()
        elif self.last_name:
            return self.last_name[:2].upper()
        return "AD"  # Default fallback

    class Meta:
        # Add indexes similar to your SQL table
        indexes = [
            models.Index(fields=['email'], name='idx_advisor_email'),
            models.Index(fields=['license_number'], name='idx_advisor_license'),
            models.Index(fields=['active'], name='idx_advisor_active'),
            models.Index(fields=['initial'], name='idx_advisor_initial'),
        ]

        # Optional: set the database table name explicitly
        db_table = 'advisor'

class Customer(models.Model):
    EMPLOYMENT_CHOICES = [
        ('Employed', 'Employed'),
        ('Self-Employed', 'Self-Employed'),
        ('Unemployed', 'Unemployed'),
        ('Retired', 'Retired'),
        ('Student', 'Student'),
    ]

    MARITAL_CHOICES = [
        ('Single', 'Single'),
        ('Married', 'Married'),
        ('Divorced', 'Divorced'),
        ('Widowed', 'Widowed'),
    ]

    customer_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField()
    alternate_email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    mobile = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=50, blank=True)
    state = models.CharField(max_length=50, blank=True)
    postal_code = models.CharField(max_length=10, blank=True)
    country = models.CharField(max_length=50, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    employment_status = models.CharField(max_length=20, choices=EMPLOYMENT_CHOICES, default='Employed')
    employer = models.CharField(max_length=100, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    annual_income = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    marital_status = models.CharField(max_length=20, choices=MARITAL_CHOICES, blank=True)
    dependents = models.IntegerField(default=0)
    advisor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    lead_source = models.CharField(max_length=50, blank=True, help_text="e.g., Referral, Website, Advertisement")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'customer'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['advisor']),
            models.Index(fields=['last_name', 'first_name']),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def get_absolute_url(self):
        return reverse('customer_detail', kwargs={'pk': self.pk})

class Mortgage(models.Model):
    MORTGAGE_TYPES = [
        ('Fixed Rate', 'Fixed Rate'),
        ('Variable Rate', 'Variable Rate'),
        ('Interest Only', 'Interest Only'),
        ('Buy-to-Let', 'Buy-to-Let'),
        ('Remortgage', 'Remortgage'),
    ]

    PROPERTY_TYPES = [
        ('House', 'House'),
        ('Flat', 'Flat'),
        ('Bungalow', 'Bungalow'),
        ('Terraced', 'Terraced'),
        ('Semi-Detached', 'Semi-Detached'),
        ('Detached', 'Detached'),
    ]

    PURPOSE_CHOICES = [
        ('Purchase', 'Purchase'),
        ('Remortgage', 'Remortgage'),
        ('Buy-to-Let', 'Buy-to-Let'),
        ('Self-Build', 'Self-Build'),
    ]

    STATUS_CHOICES = [
        ('Enquiry', 'Enquiry'),
        ('Application', 'Application'),
        ('Approved', 'Approved'),
        ('Completed', 'Completed'),
        ('Declined', 'Declined'),
        ('Withdrawn', 'Withdrawn'),
    ]

    mortgage_id = models.CharField(max_length=50,primary_key=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    advisor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    property_address = models.TextField()
    property_city = models.CharField(max_length=50, blank=True)
    property_state = models.CharField(max_length=50, blank=True)
    property_postal_code = models.CharField(max_length=10, blank=True)
    property_value = models.DecimalField(max_digits=12, decimal_places=2)
    loan_amount = models.DecimalField(max_digits=12, decimal_places=2)
    down_payment = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=3, null=True, blank=True, help_text="e.g., 3.750 for 3.75%")
    loan_term = models.IntegerField(null=True, blank=True, help_text="Loan term in years")
    mortgage_type = models.CharField(max_length=20, choices=MORTGAGE_TYPES)
    lender = models.CharField(max_length=100, blank=True)
    loan_to_value_ratio = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="LTV percentage")
    monthly_payment = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    property_type = models.CharField(max_length=20, choices=PROPERTY_TYPES, blank=True)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES, default='Purchase')
    mortgage_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Enquiry')
    application_date = models.DateField(null=True, blank=True)
    completion_date = models.DateField(null=True, blank=True)
    next_review_date = models.DateField(null=True, blank=True)
    broker_fee = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'mortgage'
        indexes = [
            models.Index(fields=['customer']),
            models.Index(fields=['advisor']),
            models.Index(fields=['mortgage_status']),
            models.Index(fields=['lender']),
            models.Index(fields=['mortgage_type']),
        ]


    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)

        # Only create application for new mortgages that don't already have one
        if is_new and not hasattr(self, 'application') and not kwargs.get('from_application', False):
            application_number = generate_application_number(
                self.advisor,
                'Mortgage'
            )
            Application.objects.create(
                customer=self.customer,
                application_type='Mortgage',
                application_status='Application Submitted',
                mortgage=self,
                advisor=self.advisor,
                application_number=application_number
            )

    def __str__(self):
        return f"{self.customer} - £{self.loan_amount} - {self.mortgage_type}"

class InsurancePolicy(models.Model):
    POLICY_TYPES = [
        ('Life Insurance', 'Life Insurance'),  # 15 chars
        ('Critical Illness', 'Critical Illness'),  # 18 chars
        ('Income Protection', 'Income Protection'),  # 18 chars
        ('Buildings Insurance', 'Buildings Insurance'),  # 20 chars
        ('Contents Insurance', 'Contents Insurance'),  # 19 chars
        ('Motor Insurance', 'Motor Insurance'),  # 16 chars
        ('Travel Insurance', 'Travel Insurance'),  # 17 chars
    ]

    FREQUENCY_CHOICES = [
        ('Monthly', 'Monthly'),
        ('Quarterly', 'Quarterly'),
        ('Semi-Annual', 'Semi-Annual'),
        ('Annual', 'Annual'),
    ]

    STATUS_CHOICES = [
        ('Quote', 'Quote'),
        ('Active', 'Active'),
        ('Lapsed', 'Lapsed'),
        ('Cancelled', 'Cancelled'),
        ('Claim Pending', 'Claim Pending'),
        ('Renewed', 'Renewed'),
    ]

    insurance_id = models.CharField(max_length=50,primary_key=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    advisor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    policy_number = models.CharField(max_length=50, unique=True, null=True, blank=True)
    policy_type = models.CharField(max_length=30, choices=POLICY_TYPES)
    coverage_amount = models.DecimalField(max_digits=12, decimal_places=2)
    premium_amount = models.DecimalField(max_digits=10, decimal_places=2)
    premium_frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='Monthly')
    insurance_company = models.CharField(max_length=100)
    policy_start_date = models.DateField()
    policy_end_date = models.DateField(null=True, blank=True)
    renewal_date = models.DateField(null=True, blank=True)
    policy_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Quote')
    underwriting_class = models.CharField(max_length=50, blank=True, help_text="e.g., Standard, Preferred, Super Preferred")
    beneficiary = models.CharField(max_length=100, blank=True)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Commission percentage")
    commission_amount = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    next_review_date = models.DateField(null=True, blank=True)
    automatic_renewal = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'insurance_policies'
        indexes = [
            models.Index(fields=['customer']),
            models.Index(fields=['advisor']),
            models.Index(fields=['policy_number']),
            models.Index(fields=['policy_type']),
            models.Index(fields=['insurance_company']),
            models.Index(fields=['policy_status']),
            models.Index(fields=['renewal_date']),
        ]

    
    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)

        # Only create application for new insurance policies that don't already have one
        if is_new and not hasattr(self, 'application') and not kwargs.get('from_application', False):
            application_number = generate_application_number(
                self.advisor,
                'Insurance',
                self.policy_type
            )
            Application.objects.create(
                customer=self.customer,
                application_type='Insurance',
                application_status='Application Submitted',
                insurance=self,
                insurance_type=self.policy_type,
                advisor=self.advisor,
                application_number=application_number
            )

    def __str__(self):
        return f"{self.customer} - {self.policy_type} - {self.policy_number}"

    @property
    def is_renewal_due(self):
        if self.renewal_date:
            return self.renewal_date <= timezone.now().date()
        return False

class Application(models.Model):
    APPLICATION_TYPES = [
        ('Mortgage', 'Mortgage'),
        ('Insurance', 'Insurance'),
        ('Both', 'Both'),
    ]

    STATUS_CHOICES = [
        ('Initial Contact', 'Initial Contact'),
        ('Documents Requested', 'Documents Requested'),
        ('Documents Received', 'Documents Received'),
        ('Application Submitted', 'Application Submitted'),
        ('Under Review', 'Under Review'),
        ('Underwriting', 'Underwriting'),
        ('Additional Info Required', 'Additional Info Required'),
        ('Approved', 'Approved'),
        ('Declined', 'Declined'),
        ('Withdrawn', 'Withdrawn'),
        ('Completed', 'Completed'),
    ]

    PRIORITY_CHOICES = [
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
        ('Urgent', 'Urgent'),
    ]
    POLICY_TYPES = [
        ('Life Insurance', 'Life Insurance'),
        ('Critical Illness', 'Critical Illness'),
        ('Income Protection', 'Income Protection'),
        ('Buildings Insurance', 'Buildings Insurance'),
        ('Contents Insurance', 'Contents Insurance'),
        ('Motor Insurance', 'Motor Insurance'),
        ('Travel Insurance', 'Travel Insurance'),
    ]

    application_id = models.AutoField(primary_key=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    mortgage = models.ForeignKey(Mortgage, on_delete=models.SET_NULL, null=True, blank=True)
    insurance = models.ForeignKey(InsurancePolicy, on_delete=models.SET_NULL, null=True, blank=True, related_name='applications')
    advisor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    solicitor_name = models.CharField(max_length=300, blank=True, null=True)
    application_type = models.CharField(max_length=20, choices=APPLICATION_TYPES)
    application_number = models.CharField(max_length=50, unique=True)
    application_status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='Initial Contact')
    application_priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='Medium')
    submitted_date = models.DateField(null=True, blank=True)
    expected_completion_date = models.DateField(null=True, blank=True)
    actual_completion_date = models.DateField(null=True, blank=True)
    decline_reason = models.TextField(blank=True)
    documents_checklist = models.JSONField(default=dict, blank=True)
    advisor_notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)
    client_communication_log = models.JSONField(default=list, blank=True)
    follow_up_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    insurance_type = models.CharField(max_length=50,choices= POLICY_TYPES, blank=True,null=True)
    # Add parent application field for "Both" type applications
    parent_application = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='child_applications'
    )

    class Meta:
        db_table = 'applications'
        indexes = [
            models.Index(fields=['customer']),
            models.Index(fields=['advisor']),
            models.Index(fields=['application_status']),
            models.Index(fields=['application_type']),
            models.Index(fields=['follow_up_date']),
            models.Index(fields=['submitted_date']),
        ]
        unique_together = ('customer', 'advisor', 'insurance_type')

    # In models.py - Update the Application model's save method
    def save(self, *args, **kwargs):
        if not self.application_number:
            # Get the current timestamp without milliseconds
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')

            # Create base pattern for counting
            base_pattern = f"APP_{self.advisor.initial}_{timestamp}"

            if self.application_type == 'Insurance' and self.insurance_type:
                # Get insurance abbreviation
                insurance_abbreviations = {
                    'Life Insurance': 'LIFE',
                    'Critical Illness': 'CI',
                    'Income Protection': 'IP',
                    'Buildings Insurance': 'BLDG',
                    'Contents Insurance': 'CNT',
                    'Motor Insurance': 'MOTOR',
                    'Travel Insurance': 'TRVL',
                    'Mortgage': 'MORT',
                    'Both': 'COMB'
                }
                prefix = insurance_abbreviations.get(self.insurance_type, 'INS')
                base_pattern = f"APP_INS_{prefix}_{self.advisor.initial}_{timestamp}"
            elif self.application_type == 'Mortgage':
                base_pattern = f"APP_MORT_{self.advisor.initial}_{timestamp}"
            else:
                base_pattern = f"APP_{self.advisor.initial}_{timestamp}"

            # Count existing applications with the same base pattern
            existing_count = Application.objects.filter(
                application_number__startswith=base_pattern
            ).count()

            # Generate the application number with sequential counter
            self.application_number = f"{base_pattern}_{existing_count + 1:03d}"

        super().save(*args, **kwargs)

    def get_related_applications(self):
        """Get all applications related to this one (children or siblings)"""
        if self.parent_application:
            # This is a child application, return all siblings
            return self.parent_application.child_applications.exclude(pk=self.pk)
        elif self.application_type == 'Both':
            # This is a parent application, return all children
            return self.child_applications.all()
        else:
            # Regular application, return empty queryset
            return Application.objects.none()

    def __str__(self):
        return f"{self.application_number} - {self.customer} - {self.application_type}"

# In models.py - update the Document model
class Document(models.Model):
    DOCUMENT_TYPES = [
        ('ID Proof', 'ID Proof'),
        ('Address Proof', 'Address Proof'),
        ('Income Proof', 'Income Proof'),
        ('Bank Statement', 'Bank Statement'),
        ('Credit Report', 'Credit Report'),
        ('Property Valuation', 'Property Valuation'),
        ('Insurance Medical', 'Insurance Medical'),
        ('Other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('Required', 'Required'),
        ('Requested', 'Requested'),
        ('Received', 'Received'),
        ('Verified', 'Verified'),
        ('Rejected', 'Rejected'),
    ]

    document_id = models.AutoField(primary_key=True)
    application = models.ForeignKey(Application, on_delete=models.CASCADE, null=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    document_name = models.CharField(max_length=255)
    # Replace file_path with document_file
    document_file = models.FileField(upload_to='documents/%Y/%m/%d/', blank=True, null=True)
    file_size = models.IntegerField(null=True, blank=True)
    mime_type = models.CharField(max_length=100, blank=True)
    document_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Required')
    requested_date = models.DateField(null=True, blank=True)
    received_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(Advisor, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    insurance = models.ForeignKey(InsurancePolicy, on_delete=models.SET_NULL, null=True, blank=True)
    mortgage = models.ForeignKey(Mortgage, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'documents'
        indexes = [
            models.Index(fields=['application']),
            models.Index(fields=['customer']),
            models.Index(fields=['document_type']),
            models.Index(fields=['document_status']),
        ]

    def save(self, *args, **kwargs):
        # Set file size and mime type when file is uploaded
        if self.document_file:
            self.file_size = self.document_file.size
            self.mime_type = self.document_file.content_type
        super().save(*args, **kwargs)

class Communication(models.Model):
    COMMUNICATION_TYPES = [
        ('Phone Call', 'Phone Call'),
        ('Email', 'Email'),
        ('SMS', 'SMS'),
        ('Meeting', 'Meeting'),
        ('Letter', 'Letter'),
        ('Video Call', 'Video Call'),
    ]

    DIRECTION_CHOICES = [
        ('Inbound', 'Inbound'),
        ('Outbound', 'Outbound'),
    ]

    communication_id = models.AutoField(primary_key=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    advisor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    application = models.ForeignKey(Application, on_delete=models.SET_NULL, null=True, blank=True)
    communication_type = models.CharField(max_length=20, choices=COMMUNICATION_TYPES)
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    subject = models.CharField(max_length=200, blank=True)
    content = models.TextField(blank=True)
    outcome = models.CharField(max_length=200, blank=True)
    follow_up_required = models.BooleanField(default=0)
    follow_up_date = models.DateField(null=True, blank=True)
    communication_date = models.DateTimeField()
    duration_minutes = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    insurance = models.ForeignKey(InsurancePolicy, on_delete=models.SET_NULL, null=True, blank=True)
    mortgage = models.ForeignKey(Mortgage, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'communications'
        indexes = [
            models.Index(fields=['customer']),
            models.Index(fields=['advisor']),
            models.Index(fields=['communication_date']),
            models.Index(fields=['follow_up_date']),
        ]


# Add to models.py
class Payment(models.Model):
    PAYMENT_METHODS = [
        ('Bank Transfer', 'Bank Transfer'),
        ('Credit Card', 'Credit Card'),
        ('Debit Card', 'Debit Card'),
        ('Cheque', 'Cheque'),
        ('Direct Debit', 'Direct Debit'),
        ('Standing Order', 'Standing Order'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Completed', 'Completed'),
        ('Failed', 'Failed'),
        ('Refunded', 'Refunded'),
    ]

    payment_id = models.AutoField(primary_key=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    application = models.ForeignKey(Application, on_delete=models.CASCADE, null=True, blank=True)
    mortgage = models.ForeignKey(Mortgage, on_delete=models.SET_NULL, null=True, blank=True)
    insurance = models.ForeignKey(InsurancePolicy, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='Pending')
    payment_date = models.DateField(null=True, blank=True)
    reference_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payments'
        indexes = [
            models.Index(fields=['customer']),
            models.Index(fields=['application']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['payment_date']),
        ]

    def __str__(self):
        return f"Payment #{self.payment_id} - £{self.amount} - {self.customer}"

# models.py - Update CommissionWeek model
class CommissionWeek(models.Model):
    STATUS_CHOICES = [
        ('Open', 'Open'),
        ('Pending Review', 'Pending Review'),
        ('Approved', 'Approved'),
        ('Paid', 'Paid'),
        ('Disputed', 'Disputed'),
    ]
    
    advisor = models.ForeignKey(Advisor, on_delete=models.CASCADE)
    week_number = models.IntegerField()
    year = models.IntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Open')
    total_estimated_commission = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_actual_commission = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='approved_weeks'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    manager_notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'commission_week'
        unique_together = ['advisor', 'week_number', 'year']
        ordering = ['-year', '-week_number']
    
    def clean(self):
        """Validate that the same advisor can't have duplicate week numbers in the same year"""
        if CommissionWeek.objects.filter(
            advisor=self.advisor,
            week_number=self.week_number,
            year=self.year
        ).exclude(pk=self.pk).exists():
            raise ValidationError(
                f"Week {self.week_number} for year {self.year} already exists for this advisor."
            )
        
        # Validate week number range
        if self.week_number < 1 or self.week_number > 53:
            raise ValidationError("Week number must be between 1 and 53")
        
        # Validate year is not in the future (optional)
        current_year = datetime.now().year
        if self.year > current_year:
            raise ValidationError("Cannot create commission weeks for future years")
    
    def save(self, *args, **kwargs):
        self.clean()  # Run validation before saving
        super().save(*args, **kwargs)
    
    def update_totals(self):
        """Update the total estimated and actual commission for this week"""
        from django.db.models import Sum
        totals = self.mappings.aggregate(
            total_estimated=Sum('estimated_commission'),
            total_actual=Sum('actual_commission')
        )
        self.total_estimated_commission = totals['total_estimated'] or 0
        self.total_actual_commission = totals['total_actual'] or 0
        self.save()

    def __str__(self):
        return f"Week {self.week_number} {self.year} - {self.advisor}"

class CommissionMapping(models.Model):
    commission_week = models.ForeignKey(CommissionWeek, on_delete=models.CASCADE, related_name='mappings')
    insurance_policy = models.ForeignKey(InsurancePolicy, on_delete=models.CASCADE)  # Remove OneToOneField for application
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    estimated_commission = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    actual_commission = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(Advisor, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_mappings')
    has_dispute = models.BooleanField(default=False)
    processing_date = models.DateField(null=True, blank=True, help_text="Date when the policy was processed")

    class Meta:
        db_table = 'commission_mapping'
        unique_together = ['commission_week', 'insurance_policy']  # Each policy can only be in a week once

    def __str__(self):
        return f"{self.commission_week} - {self.insurance_policy}"

    def save(self, *args, **kwargs):
        # Calculate estimated commission based on insurance policy
        if not self.estimated_commission and self.insurance_policy:
            self.estimated_commission = self.insurance_policy.premium_amount * (self.commission_rate / 100)
        
        # Update the parent commission week totals
        super().save(*args, **kwargs)
        self.commission_week.update_totals()

class Commission(models.Model):
    COMMISSION_TYPES = [
        ('Mortgage', 'Mortgage'),
        ('Insurance', 'Insurance'),
        ('Renewal', 'Renewal'),
        ('Referral', 'Referral'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Paid', 'Paid'),
        ('Clawed Back', 'Clawed Back'),
    ]

    commission_id = models.AutoField(primary_key=True)
    advisor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.RESTRICT)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    mortgage = models.ForeignKey(Mortgage, on_delete=models.SET_NULL, null=True, blank=True)
    insurance = models.ForeignKey(InsurancePolicy, on_delete=models.SET_NULL, null=True, blank=True)
    commission_type = models.CharField(max_length=20, choices=COMMISSION_TYPES)
    gross_amount = models.DecimalField(max_digits=10, decimal_places=2)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2)
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='Pending')
    payment_date = models.DateField(null=True, blank=True)
    tax_year = models.IntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # In Commission model, add this field:
    commission_week = models.ForeignKey(CommissionWeek, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'commissions'
        indexes = [
            models.Index(fields=['advisor']),
            models.Index(fields=['customer']),
            models.Index(fields=['commission_type']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['tax_year']),
        ]

# In models.py
class CommissionDispute(models.Model):
    DISPUTE_STATUS_CHOICES = [
        ('Open', 'Open'),
        ('In Review', 'In Review'),
        ('Resolved', 'Resolved'),
        ('Rejected', 'Rejected'),
    ]
    
    commission_mapping = models.ForeignKey(CommissionMapping, on_delete=models.CASCADE, related_name='disputes')
    raised_by = models.ForeignKey(Advisor, on_delete=models.CASCADE, related_name='disputes_raised')
    raised_date = models.DateTimeField(auto_now_add=True)
    dispute_reason = models.TextField()
    disputed_amount = models.DecimalField(max_digits=10, decimal_places=2)
    proposed_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=DISPUTE_STATUS_CHOICES, default='Open')
    resolution_notes = models.TextField(blank=True)
    resolved_by = models.ForeignKey(Advisor, on_delete=models.SET_NULL, null=True, blank=True, related_name='disputes_resolved')
    resolved_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'commission_dispute'
        ordering = ['-raised_date']
    
    def __str__(self):
        return f"Dispute #{self.id} - {self.commission_mapping.insurance_policy.policy_number}"
    
# models.py
class DailyAdvisorActivity(models.Model):
    advisor = models.ForeignKey(Advisor, on_delete=models.CASCADE)
    date = models.DateField()
    
    # Activity metrics
    calls_made = models.PositiveIntegerField(default=0)
    appointments_booked = models.PositiveIntegerField(default=0)
    appointments_attended = models.PositiveIntegerField(default=0)
    presentations_made = models.PositiveIntegerField(default=0)
    references_collected = models.PositiveIntegerField(default=0)
    brochures_sent = models.PositiveIntegerField(default=0)
    brochures_received = models.PositiveIntegerField(default=0)
    customer_introductions = models.PositiveIntegerField(default=0)
    other_sources = models.PositiveIntegerField(default=0)
    policies_sold = models.PositiveIntegerField(default=0)
    total_premium = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    home_insurance = models.PositiveIntegerField(default=0)
    pending_policies_count = models.PositiveIntegerField(default=0)
    pending_policies_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    remarks = models.TextField(blank=True)
    mortgages = models.PositiveIntegerField(default=0)
    wills = models.PositiveIntegerField(default=0)
    
    class Meta:
        db_table = 'daily_advisor_activity'
        unique_together = ['advisor', 'date']
        verbose_name_plural = 'Daily advisor activities'

class PolicySaleDetail(models.Model):
    activity = models.ForeignKey(DailyAdvisorActivity, on_delete=models.CASCADE, related_name='policy_details')
    applicant_name = models.CharField(max_length=255)
    address = models.TextField()
    contact_no = models.CharField(max_length=20)
    date_of_birth = models.DateField(null=True, blank=True)
    provider = models.CharField(max_length=255)
    life_cover_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    policy_number = models.CharField(max_length=100)
    illustration_premium = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    illustration_commission = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    new_premium = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    new_commission = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    policy_status = models.CharField(max_length=50, default='Active')
    
    # CIC (Critical Illness Cover) fields
    cic_cover_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cic_provider = models.CharField(max_length=255, blank=True)
    cic_policy_number = models.CharField(max_length=100, blank=True)
    cic_illustration_premium = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cic_illustration_commission = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cic_new_premium = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cic_new_commission = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cic_policy_status = models.CharField(max_length=50, blank=True)
    
    # IP (Income Protection) fields
    ip_cover_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    ip_provider = models.CharField(max_length=255, blank=True)
    ip_policy_number = models.CharField(max_length=100, blank=True)
    ip_illustration_premium = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    ip_illustration_commission = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    ip_new_premium = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    ip_new_commission = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    ip_policy_status = models.CharField(max_length=50, blank=True)
    
    # Accident Protection
    accident_policy_number = models.CharField(max_length=100, blank=True)
    accident_units = models.PositiveIntegerField(default=0)
    accident_premium = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        db_table = 'policy_sale_detail'