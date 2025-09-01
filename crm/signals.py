
# signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import Application, InsurancePolicy, Mortgage, DailyAdvisorActivity, PolicySaleDetail
from datetime import date

@receiver(post_save, sender=Application)
def check_application_eligibility(sender, instance, **kwargs):
    """
    Signal to check if an application is eligible for commission
    when its status changes to 'Completed'
    """
    # Only process if application status changed to 'Completed'
    if instance.application_status == 'Completed':
        # Check if this is linked to an insurance policy
        if instance.insurance:
            # Use the insurance policy, not the application instance
            if not CommissionMapping.objects.filter(insurance_policy=instance.insurance).exists():
                # Create a commission mapping or handle the case
                # where no commission mapping exists
                pass

@receiver(post_save, sender=InsurancePolicy)
def update_insurance_commission(sender, instance, **kwargs):
    """
    Update commission when insurance policy status changes
    """
    if instance.policy_status in ['Active', 'Underwriter']:
        # Find related application and update commission mapping if needed
        from .models import Application, CommissionMapping
        app = Application.objects.filter(insurance=instance).first()
        if app:
            mapping = CommissionMapping.objects.filter(application=app).first()
            if mapping:
                # Recalculate commission if needed
                pass


@receiver(post_save, sender=Application)
def update_activity_from_application(sender, instance, created, **kwargs):
    """Update activity when application status changes"""
    if instance.application_status in ['Approved', 'Completed']:
        activity, _ = DailyAdvisorActivity.objects.get_or_create(
            advisor=instance.advisor,
            date=timezone.now().date(),
            defaults={
                'policies_sold': 0,
                'total_premium': 0,
                'mortgages': 0
            }
        )
        
        if instance.application_type == 'Mortgage':
            activity.mortgages += 1
        else:
            activity.policies_sold += 1
            
        activity.save()

@receiver(post_save, sender=InsurancePolicy)
def update_activity_from_insurance(sender, instance, created, **kwargs):
    """Update activity when insurance policy is created/updated"""
    if instance.policy_status == 'Active':
        activity, _ = DailyAdvisorActivity.objects.get_or_create(
            advisor=instance.advisor,
            date=timezone.now().date(),
            defaults={
                'policies_sold': 0,
                'total_premium': 0
            }
        )
        
        activity.policies_sold += 1
        activity.total_premium += instance.premium_amount or 0
        
        # Create policy detail
        PolicySaleDetail.objects.get_or_create(
            activity=activity,
            applicant_name=f"{instance.customer.first_name} {instance.customer.last_name}",
            defaults={
                'address': instance.customer.address or '',
                'contact_no': instance.customer.phone or instance.customer.mobile or '',
                'date_of_birth': instance.customer.date_of_birth,
                'provider': instance.insurance_company,
                'life_cover_amount': instance.coverage_amount or 0,
                'policy_number': instance.policy_number or 'N/A',
                'illustration_premium': instance.premium_amount or 0,
                'illustration_commission': (instance.premium_amount * (instance.commission_rate or 0) / 100) if instance.commission_rate else 0,
                'policy_status': instance.policy_status
            }
        )
        
        activity.save()

@receiver(post_save, sender=Mortgage)
def update_activity_from_mortgage(sender, instance, created, **kwargs):
    """Update activity when mortgage is created/updated"""
    if instance.mortgage_status in ['Approved', 'Completed']:
        activity, _ = DailyAdvisorActivity.objects.get_or_create(
            advisor=instance.advisor,
            date=timezone.now().date(),
            defaults={
                'mortgages': 0
            }
        )
        
        activity.mortgages += 1
        activity.save()

@receiver(post_save, sender=Application)
def update_linked_entities(sender, instance, **kwargs):
    """
    Update mortgage and insurance status when application status changes
    """
    # Only process if this isn't a signal triggered by our own updates
    if hasattr(instance, '_updating_linked_entities'):
        return
    
    try:
        instance._updating_linked_entities = True
        
        # Update linked mortgage status
        if instance.mortgage:
            status_mapping = {
                'Approved': 'Approved',
                'Declined': 'Declined',
                'Completed': 'Completed',
                'Under Review': 'Application',
                'Initial Contact': 'Enquiry',
                'Documents Requested': 'Application',
            }
            
            if instance.application_status in status_mapping:
                new_status = status_mapping[instance.application_status]
                if instance.mortgage.mortgage_status != new_status:
                    instance.mortgage.mortgage_status = new_status
                    instance.mortgage.save()
        
        # Update linked insurance status
        if instance.insurance:
            status_mapping = {
                'Approved': 'Active',
                'Declined': 'Cancelled',
                'Completed': 'Active',
                'Under Review': 'Pending',
                'Initial Contact': 'Quote',
                'Documents Requested': 'Pending',
            }
            
            if instance.application_status in status_mapping:
                new_status = status_mapping[instance.application_status]
                if instance.insurance.policy_status != new_status:
                    instance.insurance.policy_status = new_status
                    instance.insurance.save()
    
    finally:
        # Clean up the flag
        if hasattr(instance, '_updating_linked_entities'):
            delattr(instance, '_updating_linked_entities')

@receiver(post_save, sender=InsurancePolicy)
def update_linked_application(sender, instance, **kwargs):
    """Update linked application when insurance policy changes"""
    from django.db import transaction
    
    def update_applications():
        try:
            # Use the correct reverse relationship
            related_applications = instance.applications.all()
            for application in related_applications:
                # Only update if there are actual changes to avoid recursion
                needs_update = False
                
                # Sync insurance type if different
                if application.insurance_type != instance.policy_type:
                    application.insurance_type = instance.policy_type
                    needs_update = True
                
                # Sync status if needed
                status_mapping = {
                    'Active': 'Approved',
                    'Cancelled': 'Declined',
                    'Pending': 'Under Review',
                    'Quote': 'Initial Contact',
                    'Renewed': 'Completed',
                }
                
                if instance.policy_status in status_mapping:
                    new_status = status_mapping[instance.policy_status]
                    if application.application_status != new_status:
                        application.application_status = new_status
                        needs_update = True
                
                # Only save if changes were made
                if needs_update:
                    # Disconnect signals temporarily to prevent recursion
                    from django.db.models.signals import post_save
                    from .models import Application
                    post_save.disconnect(update_linked_entities, sender=Application)
                    
                    try:
                        application.save()
                    finally:
                        # Reconnect the signal
                        post_save.connect(update_linked_entities, sender=Application)
                        
        except Exception as e:
            print(f"Error updating linked application: {str(e)}")
    
    # Defer the execution until after the transaction completes
    transaction.on_commit(update_applications)