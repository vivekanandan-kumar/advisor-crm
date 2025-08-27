# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Application, InsurancePolicy, Mortgage

@receiver(post_save, sender=Application)
def check_application_eligibility(sender, instance, **kwargs):
    """
    Check if application becomes eligible for commission and auto-assign if possible
    """
    if instance.application_status in ['Underwriting', 'Approved', 'Completed']:
        # Check if not already mapped
        from .models import CommissionApplicationMapping
        if not CommissionApplicationMapping.objects.filter(application=instance).exists():
            # Logic to auto-assign could go here, or trigger manual assignment
            pass

@receiver(post_save, sender=InsurancePolicy)
def update_insurance_commission(sender, instance, **kwargs):
    """
    Update commission when insurance policy status changes
    """
    if instance.policy_status in ['Active', 'Underwriter']:
        # Find related application and update commission mapping if needed
        from .models import Application, CommissionApplicationMapping
        app = Application.objects.filter(insurance=instance).first()
        if app:
            mapping = CommissionApplicationMapping.objects.filter(application=app).first()
            if mapping:
                # Recalculate commission if needed
                pass