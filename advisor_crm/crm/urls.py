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
    path('applications/<int:pk>/', views.ApplicationDetailView.as_view(), name='application_detail'),
    path('applications/<int:application_id>/status/', views.update_application_status, name='update_application_status'),
    path('applications/<int:pk>/edit/', ApplicationUpdateView.as_view(), name='application_update'),
    path('applications/<int:pk>/document/add/', views.add_document, name='add_document'),
    path('applications/<int:pk>/communication/add/', views.add_communication, name='add_communication'),
    path('documents/<int:pk>/edit/', views.edit_document, name='edit_document'),
    
    # Renewals and Alerts
    path('renewals/', views.renewal_alerts, name='renewal_alerts'),
    
    # Reports
    path('reports/', views.reports_view, name='reports'),
    
    # AJAX endpoints
    path('api/customers/search/', views.search_customers, name='search_customers'),
    path('api/mortgages/search/', views.mortgage_search, name='mortgage_search'),
]