# advisor_crm/urls.py (main project urls.py)
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views
from .views import AdvisorDeleteView , ApplicationUpdateView

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
    
    # Insurance URLs (if not already defined)
    path('insurance/', views.InsuranceListView.as_view(), name='insurance_list'),
    path('insurance/create/', views.InsuranceCreateView.as_view(), name='insurance_create'),
    path('insurance/<str:pk>/', views.InsuranceDetailView.as_view(), name='insurance_detail'),
    path('insurance/<str:pk>/update/', views.InsuranceUpdateView.as_view(), name='insurance_update'),
    path('insurance/<str:pk>/delete/', views.InsuranceDeleteView.as_view(), name='insurance_delete'),
    
    # Applications
    path('applications/', views.ApplicationListView.as_view(), name='application_list'),
    path('applications/add/', views.application_create_view, name='application_create'),  # Use function-based view
    path('applications/search/', views.application_search, name='application_search'),
    path('applications/<int:pk>/', views.ApplicationDetailView.as_view(), name='application_detail'),
    path('applications/<int:application_id>/status/', views.update_application_status, name='update_application_status'),
    path('applications/<int:pk>/edit/', ApplicationUpdateView.as_view(), name='application_update'),
    path('applications/<int:pk>/document/add/', views.add_document, name='add_document'),
    path('applications/<int:pk>/communication/add/', views.add_communication, name='add_communication'),
    path('documents/<int:pk>/edit/', views.edit_document, name='edit_document'),
    
    # Renewals and Alerts
    path('renewals/', views.renewal_alerts, name='renewal_alerts'),
    path('renewal-alerts/', views.renewal_alerts, name='renewal_alerts'),
    
    # Reports
    path('reports/', views.reports_view, name='reports'),
    
    # AJAX endpoints
    path('api/customers/search/', views.search_customers, name='search_customers'),
    path('api/mortgages/search/', views.mortgage_search, name='mortgage_search'),

    # Commission URLs
    path('commission/weeks/', views.commission_weeks, name='commission_weeks'),
    path('commission/week/create/', views.commission_week_create, name='commission_week_create'),
    path('commission/week/<int:pk>/', views.commission_week_detail, name='commission_week_detail'),
    path('commission/week/<int:pk>/update/', views.commission_week_update, name='commission_week_update'),
    path('commission/week/report/', views.weekly_commission_report, name='weekly_commission_report'),
    path('commission/auto-assign/', views.auto_assign_applications, name='auto_assign_applications'),

    # Payment URLs
    path('payments/', views.payment_list, name='payment_list'),
    path('payment/create/', views.payment_create, name='payment_create'),
    path('payment/<int:pk>/', views.payment_detail, name='payment_detail'),
    path('payment/<int:pk>/update/', views.payment_update, name='payment_update'),

    # Commission mapping URLs
    path('application/<int:application_id>/assign/', views.assign_application_to_week,
         name='assign_application_to_week'),
    path('mapping/<int:mapping_id>/update/', views.update_commission_mapping, name='update_commission_mapping'),
]
