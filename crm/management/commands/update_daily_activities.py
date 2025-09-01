# management/commands/update_daily_activities.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Count, Sum, Q
from crm.models import DailyAdvisorActivity, Application, InsurancePolicy, Mortgage, Communication

class Command(BaseCommand):
    help = 'Update daily advisor activities with summary data'

    def handle(self, *args, **options):
        today = timezone.now().date()
        
        # Get all advisors
        from django.contrib.auth import get_user_model
        Advisor = get_user_model()
        
        for advisor in Advisor.objects.filter(is_active=True):
            # Get or create today's activity
            activity, created = DailyAdvisorActivity.objects.get_or_create(
                advisor=advisor,
                date=today,
                defaults={
                    'calls_made': 0,
                    'appointments_booked': 0,
                    'appointments_attended': 0,
                    'presentations_made': 0
                }
            )
            
            # Update from communications (calls, meetings)
            today_comms = Communication.objects.filter(
                advisor=advisor,
                communication_date__date=today
            )
            
            activity.calls_made = today_comms.filter(
                communication_type='Phone Call'
            ).count()
            
            activity.appointments_booked = Application.objects.filter(
                advisor=advisor,
                created_at__date=today,
                application_status='Initial Contact'
            ).count()
            
            activity.appointments_attended = today_comms.filter(
                communication_type='Meeting'
            ).count()
            
            activity.presentations_made = Application.objects.filter(
                advisor=advisor,
                submitted_date=today,
                application_status='Application Submitted'
            ).count()
            
            activity.save()