# middleware.py
class ActivityTrackingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        if request.user.is_authenticated and hasattr(request.user, 'is_advisor'):
            self.track_activity(request)
            
        return response

    def track_activity(self, request):
        """Track various advisor activities in real-time"""
        from .models import DailyAdvisorActivity
        from django.utils import timezone
        
        today = timezone.now().date()
        
        # Get or create today's activity
        activity, created = DailyAdvisorActivity.objects.get_or_create(
            advisor=request.user,
            date=today,
            defaults={'calls_made': 0, 'presentations_made': 0}
        )
        
        # Track specific actions based on URL patterns
        path = request.path
        
        if '/communication/add/' in path and request.method == 'POST':
            activity.calls_made += 1
            
        elif '/application/submit/' in path and request.method == 'POST':
            activity.presentations_made += 1
            
        elif '/customer/add/' in path and request.method == 'POST':
            activity.customer_introductions += 1
            
        activity.save()