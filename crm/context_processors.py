# crm/context_processors.py
from .models import CommissionWeek

def pending_approvals(request):
    """
    Context processor to add pending approval count for managers
    """
    if request.user.is_authenticated and hasattr(request.user, 'is_manager') and request.user.is_manager:
        pending_count = CommissionWeek.objects.filter(status='Pending Review').count()
        return {'pending_approval_count': pending_count}
    return {'pending_approval_count': 0}