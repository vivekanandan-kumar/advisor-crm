# management/commands/create_sample_data.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from crm.models import Customer, Mortgage, InsurancePolicy, Application
from decimal import Decimal
import random
from datetime import datetime, timedelta

User = get_user_model()

class Command(BaseCommand):
    help = 'Create sample data for testing the CRM application'
    
    def add_arguments(self, parser):
        parser.add_argument('--advisors', type=int, default=2, help='Number of advisors to create')
        parser.add_argument('--customers', type=int, default=10, help='Number of customers per advisor')
    
    def handle(self, *args, **options):
        # Create advisors
        advisors = []
        for i in range(options['advisors']):
            advisor = User.objects.create_user(
                username=f'advisor{i+1}',
                email=f'advisor{i+1}@example.com',
                password='password123',
                first_name=f'Advisor{i+1}',
                last_name='Smith',
                license_number=f'LIC{1000+i}',
                specialization=['Mortgages', 'Insurance', 'Both'][i % 3]
            )
            advisors.append(advisor)
            self.stdout.write(f'Created advisor: {advisor.username}')
        
        # Sample data for customers
        first_names = ['John', 'Jane', 'Michael', 'Sarah', 'David', 'Lisa', 'Robert', 'Emily', 'James', 'Maria']
        last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez']
        cities = ['London', 'Manchester', 'Birmingham', 'Leeds', 'Glasgow', 'Liverpool', 'Bristol', 'Sheffield']
        
        # Create customers for each advisor
        for advisor in advisors:
            for i in range(options['customers']):
                first_name = random.choice(first_names)
                last_name = random.choice(last_names)
                
                customer = Customer.objects.create(
                    first_name=first_name,
                    last_name=last_name,
                    email=f'{first_name.lower()}.{last_name.lower()}{i}@example.com',
                    phone=f'07{random.randint(100000000, 999999999)}',
                    address=f'{random.randint(1, 999)} {random.choice(["High Street", "Park Road", "Church Lane", "Mill Lane"])}',
                    city=random.choice(cities),
                    postal_code=f'{random.choice(["SW", "NW", "SE", "NE"])}{random.randint(1, 9)} {random.randint(1, 9)}{random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")}{random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")}',
                    country='United Kingdom',
                    date_of_birth=datetime.now().date() - timedelta(days=random.randint(8000, 20000)),
                    employment_status=random.choice(['Employed', 'Self-Employed', 'Retired']),
                    annual_income=Decimal(random.randint(25000, 100000)),
                    marital_status=random.choice(['Single', 'Married', 'Divorced']),
                    dependents=random.randint(0, 3),
                    advisor=advisor,
                    lead_source=random.choice(['Website', 'Referral', 'Advertisement', 'Walk-in'])
                )
                
                # Create some mortgages
                if random.choice([True, False]):
                    mortgage = Mortgage.objects.create(
                        customer=customer,
                        advisor=advisor,
                        property_address=f'{random.randint(1, 999)} {random.choice(["Oak Avenue", "Maple Street", "Pine Close", "Cedar Road"])}',
                        property_city=random.choice(cities),
                        property_value=Decimal(random.randint(200000, 800000)),
                        loan_amount=Decimal(random.randint(150000, 600000)),
                        interest_rate=Decimal(f'{random.uniform(2.5, 5.5):.3f}'),
                        loan_term=random.choice([25, 30, 35]),
                        mortgage_type=random.choice(['Fixed Rate', 'Variable Rate', 'Buy-to-Let']),
                        lender=random.choice(['Halifax', 'Barclays', 'HSBC', 'Santander', 'Nationwide']),
                        mortgage_status=random.choice(['Application', 'Approved', 'Completed']),
                        application_date=datetime.now().date() - timedelta(days=random.randint(1, 90))
                    )
                
                # Create some insurance policies
                if random.choice([True, False]):
                    policy = InsurancePolicy.objects.create(
                        customer=customer,
                        advisor=advisor,
                        policy_number=f'POL{random.randint(100000, 999999)}',
                        policy_type=random.choice(['Life Insurance', 'Critical Illness', 'Income Protection', 'Buildings Insurance']),
                        coverage_amount=Decimal(random.randint(100000, 500000)),
                        premium_amount=Decimal(random.randint(50, 500)),
                        premium_frequency='Monthly',
                        insurance_company=random.choice(['Aviva', 'Legal & General', 'Zurich', 'AIG', 'Direct Line']),
                        policy_start_date=datetime.now().date() - timedelta(days=random.randint(1, 365)),
                        renewal_date=datetime.now().date() + timedelta(days=random.randint(1, 365)),
                        policy_status='Active'
                    )
                
                # Create applications
                if random.choice([True, False]):
                    Application.objects.create(
                        customer=customer,
                        advisor=advisor,
                        application_type=random.choice(['Mortgage', 'Insurance', 'Both']),
                        application_number=f'APP{random.randint(10000, 99999)}',
                        application_status=random.choice(['Initial Contact', 'Documents Requested', 'Under Review', 'Approved']),
                        application_priority=random.choice(['Medium', 'High', 'Low']),
                        submitted_date=datetime.now().date() - timedelta(days=random.randint(1, 30)),
                        follow_up_date=datetime.now().date() + timedelta(days=random.randint(1, 14))
                    )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {len(advisors)} advisors with {options["customers"]} customers each'
            )
        )

# utils.py
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from datetime import datetime, timedelta
from .models import InsurancePolicy, Application

def send_renewal_reminder_email(policy):
    """Send renewal reminder email for insurance policy"""
    subject = f'Policy Renewal Reminder - {policy.policy_number}'
    
    context = {
        'customer': policy.customer,
        'policy': policy,
        'advisor': policy.advisor,
    }
    
    message = render_to_string('crm/emails/renewal_reminder.html', context)
    
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[policy.customer.email, policy.advisor.email],
        html_message=message,
    )

def get_renewal_alerts(advisor, days_ahead=30):
    """Get insurance policies due for renewal"""
    today = datetime.now().date()
    future_date = today + timedelta(days=days_ahead)
    
    return InsurancePolicy.objects.filter(
        advisor=advisor,
        renewal_date__lte=future_date,
        renewal_date__gte=today,
        policy_status='Active'
    ).order_by('renewal_date')

def get_follow_up_alerts(advisor):
    """Get applications that need follow-up"""
    today = datetime.now().date()
    
    return Application.objects.filter(
        advisor=advisor,
        follow_up_date__lte=today,
        application_status__in=['Initial Contact', 'Documents Requested', 'Under Review']
    ).order_by('follow_up_date')

def calculate_commission(amount, rate):
    """Calculate commission amount"""
    return (amount * rate) / 100

def generate_application_number():
    """Generate unique application number"""
    import uuid
    return f"APP-{uuid.uuid4().hex[:8].upper()}"

# signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.mail import send_mail
from .models import Application, InsurancePolicy, Commission
from .utils import generate_application_number

@receiver(pre_save, sender=Application)
def set_application_number(sender, instance, **kwargs):
    """Automatically set application number if not provided"""
    if not instance.application_number:
        instance.application_number = generate_application_number()

@receiver(post_save, sender=Application)
def notify_status_change(sender, instance, created, **kwargs):
    """Send notification when application status changes"""
    if not created and kwargs.get('update_fields') and 'application_status' in kwargs['update_fields']:
        # Send email notification about status change
        subject = f'Application Status Updated - {instance.application_number}'
        message = f'Your application status has been updated to: {instance.application_status}'
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email='noreply@advisorcrm.com',
                recipient_list=[instance.customer.email],
                fail_silently=True,
            )
        except Exception:
            pass  # Email sending failed, but don't break the application

@receiver(post_save, sender=InsurancePolicy)
def create_commission_record(sender, instance, created, **kwargs):
    """Automatically create commission record when policy is active"""
    if created and instance.policy_status == 'Active' and instance.commission_rate:
        Commission.objects.create(
            advisor=instance.advisor,
            customer=instance.customer,
            insurance=instance,
            commission_type='Insurance',
            gross_amount=instance.premium_amount * 12,  # Annual premium
            commission_rate=instance.commission_rate,
            commission_amount=(instance.premium_amount * 12 * instance.commission_rate) / 100,
            tax_year=datetime.now().year
        )

# tasks.py (for Celery background tasks)
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import InsurancePolicy
from .utils import send_renewal_reminder_email

@shared_task
def send_renewal_reminders():
    """Send renewal reminders for policies due in 30 days"""
    today = timezone.now().date()
    reminder_date = today + timedelta(days=30)
    
    policies_due = InsurancePolicy.objects.filter(
        renewal_date=reminder_date,
        policy_status='Active',
        automatic_renewal=False
    )
    
    for policy in policies_due:
        send_renewal_reminder_email(policy)
    
    return f'Sent {policies_due.count()} renewal reminders'

@shared_task
def generate_monthly_reports():
    """Generate monthly performance reports"""
    # This would contain logic to generate and email monthly reports
    pass

# requirements.txt
Django>=4.2.0
mysqlclient>=2.1.0
Pillow>=9.0.0
celery>=5.2.0
redis>=4.0.0
django-crispy-forms>=1.14.0
django-bootstrap5>=21.3
python-decouple>=3.6
django-extensions>=3.2.0

# .env (example environment file)
SECRET_KEY=your-very-secret-key-here
DEBUG=True
DB_NAME=advisor_crm
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_HOST=localhost
DB_PORT=3306
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
            