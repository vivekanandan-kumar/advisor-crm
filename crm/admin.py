# crm/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Advisor, DailyAdvisorActivity

# Custom admin actions
def make_active(modeladmin, request, queryset):
    queryset.update(active=True)
make_active.short_description = "Mark selected advisors as active"

def make_inactive(modeladmin, request, queryset):
    queryset.update(active=False)
make_inactive.short_description = "Mark selected advisors as inactive"

@admin.register(Advisor)
class AdvisorAdmin(UserAdmin):
    actions = [make_active, make_inactive]
    
    list_display = ('username', 'email', 'first_name', 'last_name', 'license_number', 
                   'specialization', 'hire_date', 'active', 'is_staff')
    list_filter = ('active', 'is_staff', 'is_superuser', 'specialization', 'hire_date')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'license_number')
    ordering = ('last_name', 'first_name')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email', 'date_of_birth', 'phone')}),
        ('Professional Info', {'fields': ('license_number', 'specialization', 'hire_date', 'active')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 
                                   'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 
                      'first_name', 'last_name', 'date_of_birth', 'phone',
                      'license_number', 'specialization', 'hire_date', 'active'),
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
    )

class DailyAdvisorActivityAdmin(admin.ModelAdmin):
    list_display = ['advisor', 'date', 'calls_made', 'policies_sold', 'total_premium', 'mortgages']
    list_filter = ['date', 'advisor']
    search_fields = ['advisor__first_name', 'advisor__last_name']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            qs = qs.filter(advisor=request.user)
        return qs

admin.site.register(DailyAdvisorActivity, DailyAdvisorActivityAdmin)