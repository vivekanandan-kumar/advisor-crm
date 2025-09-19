# crm/tests.py

from django.test import TestCase
from django.utils import timezone
from datetime import datetime, timedelta
from .models import (
    Advisor, Customer, InsurancePolicy, Application,
    CommissionWeek, CommissionMapping
)
from decimal import Decimal

class ReportTestDataSetup(TestCase):

    def setUp(self):
        # Create a manager user
        self.manager = Advisor.objects.create_user(
            username='manager',
            email='manager@example.com',
            first_name='Molly',
            last_name='Manager',
            password='password123',
            is_manager=True,
            initial='MM'
        )

        # Create an advisor user
        self.advisor = Advisor.objects.create_user(
            username='advisor',
            email='advisor@example.com',
            first_name='Arthur',
            last_name='Advisor',
            password='password123',
            is_manager=False,
            initial='AA'
        )

        # Create a customer
        self.customer = Customer.objects.create(
            first_name='Clara',
            last_name='Client',
            email='clara.client@example.com',
            advisor=self.advisor
        )

        # Create an insurance policy using the correct field names
        self.insurance_policy = InsurancePolicy.objects.create(
            customer=self.customer,
            advisor=self.advisor,
            policy_number='INS-12345',
            policy_type='Life Insurance',
            insurance_company='Test Insurer',
            # Correct field names based on models.py
            coverage_amount=Decimal('50000.00'),
            premium_amount=Decimal('100.00'),
            commission_amount=Decimal('500.00'),
            policy_status='Active',
            policy_start_date=timezone.now().date() - timedelta(days=60), # Replaced 'issue_date'
            renewal_date=timezone.now().date() + timedelta(days=30),
            notes='Test policy for weekly report'
        )

        # Create an application linked to the insurance policy
        self.application = Application.objects.create(
            customer=self.customer,
            advisor=self.advisor,
            application_type='Insurance',
            insurance=self.insurance_policy,
            application_status='Approved',
            created_at=timezone.now() - timedelta(days=60)
        )

        # Create a CommissionWeek
        self.commission_week = CommissionWeek.objects.create(
            advisor=self.advisor,
            start_date=timezone.now().date() - timedelta(days=7),
            end_date=timezone.now().date() - timedelta(days=1),
            year=timezone.now().year,
            week_number=datetime.now().isocalendar()[1] - 1,
            status='Pending Review'
        )

        # Create a CommissionMapping
        self.commission_mapping = CommissionMapping.objects.create(
            commission_week=self.commission_week,
            insurance_policy=self.insurance_policy,
            estimated_commission=Decimal('500.00'),
            actual_commission=Decimal('485.00'),
            commission_rate=Decimal('10.00')
        )

    def test_data_integrity(self):
        """Test that the created objects are linked correctly."""
        self.assertEqual(self.customer.advisor, self.advisor)
        self.assertEqual(self.insurance_policy.customer, self.customer)
        self.assertEqual(self.application.insurance, self.insurance_policy)
        self.assertEqual(self.commission_mapping.insurance_policy, self.insurance_policy)
        self.assertEqual(self.commission_mapping.commission_week, self.commission_week)

    def test_commission_mapping_data(self):
        """Test that the commission data is as expected."""
        self.assertEqual(self.commission_mapping.estimated_commission, Decimal('500.00'))
        self.assertEqual(self.commission_mapping.actual_commission, Decimal('485.00'))
        self.assertEqual(self.commission_mapping.commission_rate, Decimal('10.00'))