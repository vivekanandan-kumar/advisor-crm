# advisor_crm/urls.py (main project URLs)
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views


urlpatterns = [
     # Authentication URLs
    path('login/', auth_views.LoginView.as_view(template_name='crm/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='crm/logout.html'), name='logout'),
    path('admin/', admin.site.urls),
    path('', include('crm.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


# admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from crm.models import (
    Advisor, Customer, Mortgage, InsurancePolicy,
    Application, Document, Communication, Commission
)

class AdvisorAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'license_number', 'specialization', 'active')
    list_filter = ('active', 'specialization', 'hire_date')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'license_number')

    fieldsets = UserAdmin.fieldsets + (
        ('Advisor Information', {
            'fields': ('license_number', 'specialization', 'phone', 'hire_date', 'active')
        }),
    )

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'advisor', 'employment_status', 'created_at')
    list_filter = ('advisor', 'employment_status', 'marital_status', 'created_at')
    search_fields = ('first_name', 'last_name', 'email')
    date_hierarchy = 'created_at'

@admin.register(Mortgage)
class MortgageAdmin(admin.ModelAdmin):
    list_display = ('customer', 'loan_amount', 'mortgage_type', 'mortgage_status', 'lender', 'application_date')
    list_filter = ('mortgage_type', 'mortgage_status', 'lender', 'advisor')
    search_fields = ('customer__first_name', 'customer__last_name', 'lender', 'property_address')
    date_hierarchy = 'application_date'

@admin.register(InsurancePolicy)
class InsurancePolicyAdmin(admin.ModelAdmin):
    list_display = ('customer', 'policy_type', 'policy_number', 'insurance_company', 'policy_status', 'renewal_date')
    list_filter = ('policy_type', 'policy_status', 'insurance_company', 'advisor')
    search_fields = ('customer__first_name', 'customer__last_name', 'policy_number', 'insurance_company')
    date_hierarchy = 'renewal_date'

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('application_number', 'customer', 'application_type', 'application_status', 'application_priority', 'submitted_date')
    list_filter = ('application_type', 'application_status', 'application_priority', 'advisor')
    search_fields = ('application_number', 'customer__first_name', 'customer__last_name')
    date_hierarchy = 'submitted_date'

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('document_name', 'customer', 'document_type', 'document_status', 'received_date')
    list_filter = ('document_type', 'document_status', 'uploaded_by')
    search_fields = ('document_name', 'customer__first_name', 'customer__last_name')

@admin.register(Communication)
class CommunicationAdmin(admin.ModelAdmin):
    list_display = ('customer', 'communication_type', 'direction', 'subject', 'communication_date', 'advisor')
    list_filter = ('communication_type', 'direction', 'advisor')
    search_fields = ('customer__first_name', 'customer__last_name', 'subject', 'content')
    date_hierarchy = 'communication_date'

@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    list_display = ('advisor', 'customer', 'commission_type', 'commission_amount', 'payment_status', 'payment_date')
    list_filter = ('commission_type', 'payment_status', 'advisor', 'tax_year')
    search_fields = ('advisor__first_name', 'advisor__last_name', 'customer__first_name', 'customer__last_name')
    date_hierarchy = 'payment_date'
