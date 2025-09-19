# advisor_crm/urls.py (main project urls.py)
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views
from .views import AdvisorDeleteView , ApplicationUpdateView, CommissionWeeksListView,commission_week_detail,submit_week_for_approval,WeeklyCommissionReportView,UpdateCommissionMappingView, export_advisor_report


urlpatterns = [
 
    path('', views.home_page, name='home_page'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),


    # Advisor
    path('advisor/', views.AdvisorListView.as_view(), name='advisor_list'),
    path('advisor/add/', views.AdvisorCreateView.as_view(), name='advisor_create'),
    path('advisor/<int:pk>/', views.AdvisorDetailView.as_view(), name='advisor_detail'),
    path('advisor/<int:pk>/edit/', views.AdvisorUpdateView.as_view(), name='advisor_update'),
    path('advisor/<int:pk>/delete/', AdvisorDeleteView.as_view(), name='advisor_delete'),
        
    # Customers
    path('customers/', views.CustomerListView.as_view(), name='customer_list'),
    path('customers/add/', views.CustomerCreateView.as_view(), name='customer_create'),
    path('customers/<int:pk>/', views.CustomerDetailView.as_view(), name='customer_detail'),
    path('customers/<int:pk>/edit/', views.CustomerUpdateView.as_view(), name='customer_update'),
    path('customers/<int:customer_id>/communication/add/', views.communication_create, name='communication_create'),
    
    # Mortgage URLs
    path('mortgages/', views.MortgageListView.as_view(), name='mortgage_list'),
    path('mortgages/create/', views.MortgageCreateView.as_view(), name='mortgage_create'),
    path('mortgages/<str:pk>/', views.MortgageDetailView.as_view(), name='mortgage_detail'),
    path('mortgages/<str:pk>/update/', views.MortgageUpdateView.as_view(), name='mortgage_update'),
    path('mortgages/<str:pk>/delete/', views.MortgageDeleteView.as_view(), name='mortgage_delete'),
    path('mortgage/<str:mortgage_id>/document/add/', views.mortgage_document_create, name='mortgage_document_create'),

    # Insurance URLs (if not already defined)
    path('insurance/', views.InsuranceListView.as_view(), name='insurance_list'),
    path('insurance/create/', views.InsuranceCreateView.as_view(), name='insurance_create'),
    path('insurance/<str:pk>/', views.InsuranceDetailView.as_view(), name='insurance_detail'),
    path('insurance/<str:pk>/update/', views.InsuranceUpdateView.as_view(), name='insurance_update'),
    path('insurance/<str:pk>/delete/', views.InsuranceDeleteView.as_view(), name='insurance_delete'),
    path('insurance/<str:insurance_id>/communication/add/', views.insurance_communication_create, name='insurance_communication_create'),
    path('insurance/<str:pk>/document/add/', views.add_document, name='add_document'),
    path('insurance/<str:insurance_id>/communications/<int:pk>/edit/', views.insurance_communication_edit, name='insurance_communication_edit'),

    # Applications
    path('applications/', views.ApplicationListView.as_view(), name='application_list'),
    path('applications/add/', views.application_create_view, name='application_create'),  # Use function-based view
    path('applications/search/', views.application_search, name='application_search'),
    path('applications/<int:pk>/', views.ApplicationDetailView.as_view(), name='application_detail'),
    path('applications/<int:pk>/edit/', ApplicationUpdateView.as_view(), name='application_update'),
    path('applications/<int:pk>/document/add/', views.add_document, name='add_document'),
    path('applications/<int:pk>/communication/add/', views.application_communication_create, name='application_communication_create'),
    path('documents/<int:pk>/edit/', views.edit_document, name='edit_document'),
    path('documents/create/', views.DocumentCreateView.as_view(), name='document_create'),
    path('documents/<int:pk>/edit/', views.DocumentEditView.as_view(), name='document_edit'),
    # Renewals and Alerts
    path('renewals/', views.renewal_alerts, name='renewal_alerts'),
    path('renewal-alerts/', views.renewal_alerts, name='renewal_alerts'),
    
    # Reports
    path('reports/', views.reports_view, name='reports'),
    
    # AJAX endpoints
    path('api/customers/search/', views.search_customers, name='search_customers'),
    path('api/mortgages/search/', views.search_mortgages, name='search_mortgages'),

    # Commission URLs
    path('commission/weeks/', views.commission_weeks, name='commission_weeks'),
    path('commission/week/<int:pk>/', views.commission_week_detail, name='commission_week_detail'),
    path('commission/week/create/', views.commission_week_create, name='commission_week_create'),
    path('commission/week/<int:pk>/edit/', views.commission_week_update, name='commission_week_update'),
    path('commission/week/<int:pk>/update/', views.commission_week_update, name='commission_week_update'),
    path('commission/week/<int:pk>/submit/', views.submit_week_for_approval, name='submit_week_for_approval'),
    path('commission/week/report/', views.weekly_commission_report, name='weekly_commission_report'),
    path('auto-assign-applications/', views.auto_assign_applications, name='auto_assign_applications'),
    
    path('commission-weeks/', CommissionWeeksListView.as_view(), name='commission_weeks'),
    path('commission-mapping/<int:pk>/update/', UpdateCommissionMappingView.as_view(), name='update_commission_mapping'),
    path('commission-report/', WeeklyCommissionReportView.as_view(), name='weekly_commission_report'),
    path('commission/', views.commission_report, name='commission_report'),
    path('commission/week/new/', views.commission_week_create, name='commission_week_create'),
    
    path('commission/auto-assign/', views.auto_assign_applications, name='auto_assign_applications'),

    # Payment URLs
    path('payments/', views.payment_list, name='payment_list'),
    path('payment/create/', views.payment_create, name='payment_create'),
    path('payment/<int:pk>/', views.payment_detail, name='payment_detail'),
    path('payment/<int:pk>/update/', views.payment_update, name='payment_update'),

    # Commission mapping URLs
    path('commission-week/<int:week_id>/add-insurance/', views.add_insurance_to_week, name='add_insurance_to_week'),
    path('commission-mapping/<int:mapping_id>/update/', views.update_commission_mapping, name='update_commission_mapping'),
    path('mapping/<int:mapping_id>/update/', views.update_commission_mapping, name='update_commission_mapping'),
    
    
    # Manager-specific URLs
    path('manager/commission-weeks/', views.manager_commission_weeks, name='manager_commission_weeks'),
    path('commission-week/<int:pk>/approve/', views.commission_week_approval, name='commission_week_approval'),
    path('update-insurance-commission/', views.update_insurance_commission, name='update_insurance_commission'),
    path('refresh-insurance-data/', views.refresh_insurance_data, name='refresh_insurance_data'),

    # In Dispute
    path('dispute/raise/<int:mapping_id>/', views.raise_commission_dispute, name='raise_dispute'),
    path('dispute/resolve/<int:dispute_id>/', views.resolve_commission_dispute, name='resolve_dispute'),
    path('disputes/', views.view_disputes, name='view_disputes'),

    # Add this URL for advisor weekly report export
    path('advisor-weekly-report/', views.advisor_weekly_report, name='advisor_weekly_report'),
    path('export-advisor-report/', views.export_advisor_report, name='export_advisor_report'),
]
