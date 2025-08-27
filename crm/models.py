# models.py
from django.contrib.auth import get_user_model
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.urls import reverse
from django.utils import timezone
import json
from django.conf import settings
import uuid

def generate_mortgage_id():
    # This function creates a unique, human-readable ID
    # Adjust the format 'INS_{...}' to match your requirements
    from datetime import datetime
    now = datetime.now()
    timestamp = now.strftime('%Y%m%d%H%M%S')
    # Use a part of a UUID for extra uniqueness
    unique_part = str(uuid.uuid4())[:6]
    return f"MRT_{timestamp}_{unique_part}"

def generate_insurance_id():
    # This function creates a unique, human-readable ID
    # Adjust the format 'INS_{...}' to match your requirements
    from datetime import datetime
    now = datetime.now()
    timestamp = now.strftime('%Y%m%d%H%M%S')
    # Use a part of a UUID for extra uniqueness
    unique_part = str(uuid.uuid4())[:6]
    return f"INS_{timestamp}_{unique_part}"

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

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        # Add indexes similar to your SQL table
        indexes = [
            models.Index(fields=['email'], name='idx_advisor_email'),
            models.Index(fields=['license_number'], name='idx_advisor_license'),
            models.Index(fields=['active'], name='idx_advisor_active'),
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

    mortgage_id = models.CharField(max_length=50,primary_key=True,
        default=generate_insurance_id,  # Use the custom function here
        )
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
        if not self.mortgage_id:  # Only for new instances
            # Generate mortgage ID in the format: MRT-ADVISOR_ID-YYYYMMDDHHMISS
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            self.mortgage_id = f"MRT-{self.advisor.id}-{timestamp}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.customer} - £{self.loan_amount} - {self.mortgage_type}"

class InsurancePolicy(models.Model):
    POLICY_TYPES = [
        ('Life Insurance', 'Life Insurance'),
        ('Critical Illness', 'Critical Illness'),
        ('Income Protection', 'Income Protection'),
        ('Buildings Insurance', 'Buildings Insurance'),
        ('Contents Insurance', 'Contents Insurance'),
        ('Motor Insurance', 'Motor Insurance'),
        ('Travel Insurance', 'Travel Insurance'),
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

    insurance_id = models.CharField(max_length=50,primary_key=True,
                                    default=generate_insurance_id,
                                    )
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
        if not self.insurance_id:  # Only for new instances
            # Generate insurance ID in the format: INS-ADVISOR_ID-YYYYMMDDHHMISS
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            self.insurance_id = f"INS-{self.advisor.id}-{timestamp}"
        super().save(*args, **kwargs)

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
    insurance = models.ForeignKey(InsurancePolicy, on_delete=models.SET_NULL, null=True, blank=True)
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

    def save(self, *args, **kwargs):
        if not self.application_number:  # Generate application number if not set
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')

            # Create insurance type abbreviation mapping
            insurance_abbreviations = {
                'Life Insurance': 'INS_LIFE',
                'Critical Illness': 'INS_CI',
                'Income Protection': 'INS_IP',
                'Buildings Insurance': 'INS_BLDG',
                'Contents Insurance': 'INS_CNT',
                'Motor Insurance': 'INS_MOTOR',
                'Travel Insurance': 'INS_TRVL',
                'Mortgage': 'MORT',  # For mortgage applications
                'Both': 'COMB'       # For combined applications
            }

            # Determine the prefix based on application type
            if self.application_type == 'Insurance' and self.insurance_type:
                prefix = insurance_abbreviations.get(self.insurance_type, 'INS')
                app_number = f"APP-{prefix}_{self.advisor.id}_{timestamp}"
            elif self.application_type == 'Mortgage':
                prefix = 'MORT'
                app_number = f"APP-{prefix}_{self.advisor.id}_{timestamp}"
            elif self.application_type == 'Both':
                prefix = 'COMB'
                app_number = f"APP_{prefix}-{self.advisor.id}_{timestamp}"
            else:
                prefix = 'APP'  # Default fallback
                app_number = f"{prefix}_{self.advisor.id}_{timestamp}"

            self.application_number = app_number
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.application_number} - {self.customer} - {self.application_type}"

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
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    document_name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500, blank=True)
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

    class Meta:
        db_table = 'documents'
        indexes = [
            models.Index(fields=['application']),
            models.Index(fields=['customer']),
            models.Index(fields=['document_type']),
            models.Index(fields=['document_status']),
        ]

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


class CommissionWeek(models.Model):
    week_id = models.AutoField(primary_key=True)
    week_number = models.IntegerField()  # 1-52
    year = models.IntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    advisor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    total_estimated_commission = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_actual_commission = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=[
        ('Open', 'Open'),
        ('Pending Review', 'Pending Review'),
        ('Approved', 'Approved'),
        ('Paid', 'Paid')
    ], default='Open')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'commission_weeks'
        unique_together = ['week_number', 'year', 'advisor']
        indexes = [
            models.Index(fields=['advisor']),
            models.Index(fields=['week_number', 'year']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Week {self.week_number} {self.year} - {self.advisor}"

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


class CommissionApplicationMapping(models.Model):
    mapping_id = models.AutoField(primary_key=True)
    application = models.OneToOneField(Application, on_delete=models.CASCADE)
    commission_week = models.ForeignKey(CommissionWeek, on_delete=models.CASCADE)
    estimated_commission = models.DecimalField(max_digits=10, decimal_places=2)
    actual_commission = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'commission_application_mappings'
        unique_together = ['application', 'commission_week']
        indexes = [
            models.Index(fields=['application']),
            models.Index(fields=['commission_week']),
        ]

    def __str__(self):
        return f"{self.application} -> Week {self.commission_week.week_number}"