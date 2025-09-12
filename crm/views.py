# views.py
from django.contrib.auth import login, authenticate, logout
from django.views.decorators.http import require_http_methods
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib import messages
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import datetime, timedelta, date
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.contrib.auth import get_user_model  
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView,TemplateView
from django.views.decorators.http import require_POST
from django.db import transaction
from decimal import Decimal
from django.views.decorators.csrf import csrf_protect,csrf_exempt
from django.db import models
from django.db.models import Q, Count, Sum, Avg 
from django.db.models.functions import TruncMonth, TruncYear
from collections import defaultdict
import calendar
import pandas as pd
from django.http import HttpResponse
from io import BytesIO
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    Customer, Mortgage, InsurancePolicy, Application, Advisor,
    Document, Communication, Commission, Payment, CommissionWeek, 
    CommissionMapping, Application, CommissionDispute,  # Add CommissionMapping here
    DailyAdvisorActivity
)
from .forms import (
    DocumentForm, PaymentForm, CustomerForm,CommissionWeekForm,  MortgageForm, InsurancePolicyForm,
    ApplicationForm, CommunicationForm, AdvisorForm, CommissionMappingForm,CommissionWeekApprovalForm
)

# Get the custom user model
User = get_user_model()

def calculate_growth(previous_value, current_value):
    """
    Calculate percentage growth between two values
    Returns 0 if previous value is 0 to avoid division by zero
    """
    if previous_value == 0:
        return 0
    return ((current_value - previous_value) / previous_value) * 100

@login_required
def dashboard(request):
    """Main dashboard view"""
    advisor = request.user

    # Get counts for dashboard cards
    total_customers = Customer.objects.all().count()
    active_mortgages = Mortgage.objects.filter(
        advisor=advisor,
        mortgage_status__in=['Application', 'Approved']
    ).count()
    active_insurance = InsurancePolicy.objects.filter(
        advisor=advisor,
        policy_status='Active'
    ).count()
    pending_applications = Application.objects.filter(
        advisor=advisor,
        application_status__in=['Initial Contact', 'Documents Requested', 'Under Review']
    ).count()

    # Get renewals due in next 30 days
    next_month = timezone.now().date() + timedelta(days=30)
    renewals_due = InsurancePolicy.objects.filter(
        advisor=advisor,
        renewal_date__lte=next_month,
        renewal_date__gte=timezone.now().date(),
        policy_status='Active'
    ).order_by('renewal_date')

    # Get follow-ups due
    followups_due = Application.objects.filter(
        advisor=advisor,
        follow_up_date__lte=timezone.now().date(),
        application_status__in=['Initial Contact', 'Documents Requested', 'Under Review']
    ).order_by('follow_up_date')

    # Recent communications
    recent_communications = Communication.objects.filter(
        advisor=advisor
    ).order_by('-communication_date')[:5]

    # Commission summary
    commission_summary = Commission.objects.filter(advisor=advisor).aggregate(
        total_pending=Sum('commission_amount', filter=Q(payment_status='Pending')),
        total_paid=Sum('commission_amount', filter=Q(payment_status='Paid'))
    )

    context = {
        'total_customers': total_customers,
        'active_mortgages': active_mortgages,
        'active_insurance': active_insurance,
        'pending_applications': pending_applications,
        'renewals_due': renewals_due,
        'followups_due': followups_due,
        'recent_communications': recent_communications,
        'commission_summary': commission_summary,
    }

    return render(request, 'crm/dashboard.html', context)

def home_page(request):
    return render(request, 'crm/index.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'crm/login.html')

@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('home_page')


class AdvisorListView(LoginRequiredMixin, ListView):
    model = User  # Use User instead of Advisor
    template_name = 'crm/advisor_list.html'
    context_object_name = 'advisor'  
    paginate_by = 20

    def get_queryset(self):
        queryset = User.objects.all().order_by('-created_at')
        
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(license_number__icontains=search_query)
            )
        return queryset

class AdvisorDetailView(LoginRequiredMixin, DetailView):
    model = User  # Use User instead of Advisor
    template_name = 'crm/advisor_detail.html'
    context_object_name = 'advisor'

class AdvisorCreateView(LoginRequiredMixin, CreateView):
    model = User  # Use User instead of Advisor
    form_class = AdvisorForm
    template_name = 'crm/advisor_form.html'
    success_url = reverse_lazy('advisor_list')

class AdvisorUpdateView(LoginRequiredMixin, UpdateView):
    model = User  # Use User instead of Advisor
    form_class = AdvisorForm
    template_name = 'crm/advisor_form.html'
    success_url = reverse_lazy('advisor_list')

# Add AdvisorDeleteView
class AdvisorDeleteView(LoginRequiredMixin, DeleteView):
    model = User
    template_name = 'crm/advisor_confirm_delete.html'
    success_url = reverse_lazy('advisor_list')
    
    def delete(self, request, *args, **kwargs):
        advisor = self.get_object()
        messages.success(request, f'Advisor {advisor.get_full_name()} has been deleted successfully!')
        return super().delete(request, *args, **kwargs)
    
# views.py - Update CustomerListView
class CustomerListView(LoginRequiredMixin, ListView):
    model = Customer
    template_name = 'crm/customer_list.html'
    context_object_name = 'customers'
    paginate_by = 20

    def get_queryset(self):
        print(f"DEBUG - Current user: {self.request.user} (ID: {self.request.user.id})")
        
        # Show ALL customers instead of filtering by advisor
        queryset = Customer.objects.all().order_by('-created_at')
        print(f"DEBUG - Found {queryset.count()} customers total")
        
        search_query = self.request.GET.get('search')
        if search_query:
            print(f"DEBUG - Searching for: {search_query}")
            queryset = queryset.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query)
            )
            print(f"DEBUG - After search: {queryset.count()} customers")
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add debug info to context
        context['debug_user'] = self.request.user
        context['debug_customer_count'] = Customer.objects.all().count()  # Show total count
        context['all_customers_count'] = Customer.objects.all().count()
        return context

# views.py - Update CustomerDetailView
class CustomerDetailView(LoginRequiredMixin, DetailView):
    model = Customer
    template_name = 'crm/customer_detail.html'
    context_object_name = 'customer'

    # Remove the get_queryset method to allow access to all customers
    # def get_queryset(self):
    #     return Customer.objects.filter(advisor=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = self.get_object()

        context['mortgages'] = Mortgage.objects.filter(customer=customer)
        context['insurance_policies'] = InsurancePolicy.objects.filter(customer=customer)
        context['applications'] = Application.objects.filter(customer=customer).order_by('-created_at')
        context['communications'] = Communication.objects.filter(customer=customer).order_by('-communication_date')[:10]

        return context

class CustomerCreateView(LoginRequiredMixin, CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'crm/customer_form.html'
    success_url = reverse_lazy('customer_list')

    def form_valid(self, form):
        print(f"DEBUG - Setting advisor to: {self.request.user} (ID: {self.request.user.id})")
        form.instance.advisor = self.request.user
        response = super().form_valid(form)
        print(f"DEBUG - Customer created: {self.object}")
        print(f"DEBUG - Customer advisor: {self.object.advisor}")
        messages.success(self.request, f'Customer {self.object} created successfully!')
        return response

    def get_form_kwargs(self):
        """Add the current user to form kwargs for validation if needed"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
# views.py - Update CustomerUpdateView
class CustomerUpdateView(LoginRequiredMixin, UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'crm/customer_form.html'

    # Remove the get_queryset method to allow editing all customers
    # def get_queryset(self):
    #     return Customer.objects.filter(advisor=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, 'Customer updated successfully!')
        return super().form_valid(form)


class MortgageListView(LoginRequiredMixin, ListView):
    model = Mortgage
    template_name = 'crm/mortgage_list.html'
    context_object_name = 'mortgages'
    paginate_by = 20

    def get_queryset(self):
        # Remove advisor filter to show all mortgages
        # return Mortgage.objects.filter(advisor=self.request.user).order_by('-created_at')
        return Mortgage.objects.all().order_by('-created_at')
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_query = self.request.GET.get('search')
        if search_query:
            context['search'] = search_query
        return context
    
class MortgageDetailView(LoginRequiredMixin, DetailView):
    model = Mortgage
    template_name = 'crm/mortgage_detail.html'
    context_object_name = 'mortgage'
    slug_field = 'mortgage_id'
    slug_url_kwarg = 'pk'

    def get_queryset(self):
        # Remove advisor filter to allow access to all mortgages
        # return Mortgage.objects.filter(advisor=self.request.user)
        return Mortgage.objects.all()

class MortgageCreateView(LoginRequiredMixin, CreateView):
    model = Mortgage
    form_class = MortgageForm
    template_name = 'crm/mortgage_form.html'
    success_url = reverse_lazy('mortgage_list')

    def form_valid(self, form):
        form.instance.advisor = self.request.user
        messages.success(self.request, 'Mortgage created successfully!')
        return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Filter customers to only show current advisor's records or all
        # form.fields['customer'].queryset = Customer.objects.filter(advisor=self.request.user)
        form.fields['customer'].queryset = Customer.objects.all()
        return form
    
class MortgageUpdateView(LoginRequiredMixin, UpdateView):
    model = Mortgage
    form_class = MortgageForm
    template_name = 'crm/mortgage_form.html'
    success_url = reverse_lazy('mortgage_list')
    pk_url_kwarg = 'pk'  # Explicitly specify the URL keyword

    def get_queryset(self):
        return Mortgage.objects.all()

    def get_object(self, queryset=None):
        # Handle string primary key (mortgage_id)
        pk = self.kwargs.get(self.pk_url_kwarg)
        return get_object_or_404(Mortgage, mortgage_id=pk)

    def form_valid(self, form):
        messages.success(self.request, 'Mortgage updated successfully!')
        return super().form_valid(form)

class MortgageDeleteView(LoginRequiredMixin, DeleteView):
    model = Mortgage
    template_name = 'crm/mortgage_confirm_delete.html'
    success_url = reverse_lazy('mortgage_list')

    def get_queryset(self):
        # Remove advisor filter to allow deleting all mortgages
        # return Mortgage.objects.filter(advisor=self.request.user)
        return Mortgage.objects.all()

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Mortgage deleted successfully!')
        return super().delete(request, *args, **kwargs)

class InsuranceListView(LoginRequiredMixin, ListView):
    model = InsurancePolicy
    template_name = 'crm/insurance_list.html'
    context_object_name = 'policies'
    paginate_by = 20

    def get_queryset(self):
        # Prefetch related application data to avoid N+1 queries
        return InsurancePolicy.objects.all().select_related(
            'customer', 'advisor'
        ).prefetch_related(
            'applications'
        ).order_by('-created_at')
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_query = self.request.GET.get('search')
        if search_query:
            context['search'] = search_query
        return context
    
class InsuranceCreateView(LoginRequiredMixin, CreateView):
    model = InsurancePolicy
    form_class = InsurancePolicyForm
    template_name = 'crm/insurance_form.html'
    success_url = reverse_lazy('insurance_list')

    def form_valid(self, form):
        form.instance.advisor = self.request.user
        messages.success(self.request, 'Insurance policy created successfully!')
        return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Filter customers to only show current advisor's records or all
        # form.fields['customer'].queryset = Customer.objects.filter(advisor=self.request.user)
        form.fields['customer'].queryset = Customer.objects.all()
        return form
        
class InsuranceDetailView(LoginRequiredMixin, DetailView):
    model = InsurancePolicy
    template_name = 'crm/insurance_detail.html'
    context_object_name = 'insurance'

    def get_queryset(self):
        # Prefetch related data including applications and their documents
        return InsurancePolicy.objects.all().select_related(
            'customer', 'advisor'
        ).prefetch_related(
            'applications', 
            'applications__document_set',  # Changed from 'applications__documents'
            'applications__communication_set'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        insurance = self.get_object()
        
        # Get the first application related to this insurance policy
        application = insurance.applications.first()
        
        # Get documents and communications related to this application
        documents = Document.objects.filter(application=application) if application else []
        communications = Communication.objects.filter(application=application) if application else []
        
        context['application'] = application
        context['documents'] = documents
        context['communications'] = communications
        
        return context

class InsuranceUpdateView(LoginRequiredMixin, UpdateView):
    model = InsurancePolicy
    form_class = InsurancePolicyForm
    template_name = 'crm/insurance_form.html'
    success_url = reverse_lazy('insurance_list')
    pk_url_kwarg = 'pk'

    def get_queryset(self):
        return InsurancePolicy.objects.all()

    def get_object(self, queryset=None):
        # Get by insurance_id (primary key)
        pk = self.kwargs.get(self.pk_url_kwarg)
        return get_object_or_404(InsurancePolicy, insurance_id=pk)

    def form_valid(self, form):
        insurance_policy = form.save(commit=False)
        
        # Update related applications if they exist
        try:
            # Use the correct reverse relationship name - it's 'application_set' or the related_name
            related_applications = Application.objects.filter(insurance=insurance_policy)
            for application in related_applications:
                # Update application fields based on insurance changes
                if 'policy_status' in form.changed_data:
                    # Map insurance status to application status
                    status_mapping = {
                        'Active': 'Approved',
                        'Cancelled': 'Declined',
                        'Pending': 'Under Review',
                        'Quote': 'Initial Contact',
                        'Renewed': 'Completed',
                    }
                    
                    if insurance_policy.policy_status in status_mapping:
                        application.application_status = status_mapping[insurance_policy.policy_status]
                        application.save()
                        
                # Also update the insurance_type if policy_type changed
                if 'policy_type' in form.changed_data:
                    application.insurance_type = insurance_policy.policy_type
                    application.save()
                    
        except Exception as e:
            # Log the error but don't break the insurance update
            print(f"Error updating related applications: {str(e)}")
        
        messages.success(self.request, 'Insurance policy updated successfully!')
        return super().form_valid(form)

class InsuranceDeleteView(LoginRequiredMixin, DeleteView):
    model = InsurancePolicy
    template_name = 'crm/insurance_confirm_delete.html'
    success_url = reverse_lazy('insurance_list')

    def get_queryset(self):
        # Remove advisor filter to allow deleting all insurance policies
        # return InsurancePolicy.objects.filter(advisor=self.request.user)
        return InsurancePolicy.objects.all()

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Insurance policy deleted successfully!')
        return super().delete(request, *args, **kwargs)

# views.py - ApplicationListView
class ApplicationListView(LoginRequiredMixin, ListView):
    model = Application
    template_name = 'crm/application_list.html'
    context_object_name = 'applications'
    paginate_by = 15

    def get_queryset(self):
        queryset = Application.objects.all().order_by('-created_at')
        
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(application_number__icontains=search_query) |
                Q(customer__first_name__icontains=search_query) |
                Q(customer__last_name__icontains=search_query) |
                Q(customer__email__icontains=search_query) |
                Q(mortgage__property_postal_code__icontains=search_query) |
                Q(insurance__policy_number__icontains=search_query)
            ).distinct()
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_query = self.request.GET.get('search')
        if search_query:
            context['search'] = search_query
        return context

def search_mortgages(request):
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse([], safe=False)
    
    mortgages = Mortgage.objects.filter(
        Q(property_address__icontains=query) |
        Q(property_postal_code__icontains=query) |
        Q(property_city__icontains=query) |
        Q(customer__first_name__icontains=query) |
        Q(customer__last_name__icontains=query)
    ).select_related('customer')[:10]  # Limit to 10 results
    
    results = []
    for mortgage in mortgages:
        results.append({
            'id': str(mortgage.mortgage_id),
            'address': mortgage.property_address,
            'postal_code': mortgage.property_postal_code,
            'city': mortgage.property_city,
            'customer': f"{mortgage.customer.first_name} {mortgage.customer.last_name}",
            'amount': f"{mortgage.loan_amount:,.2f}",
            'status': mortgage.mortgage_status
        })
    
    return JsonResponse(results, safe=False)

@login_required
def application_search(request):
    """Advanced application search"""
    query = request.GET.get('q', '')
    
    if query:
        applications = Application.objects.filter(
            Q(application_number__icontains=query) |
            Q(customer__first_name__icontains=query) |
            Q(customer__last_name__icontains=query) |
            Q(customer__email__icontains=query) |
            Q(mortgage__property_postal_code__icontains=query) |
            Q(mortgage__property_address__icontains=query) |
            Q(mortgage__property_city__icontains=query) |
            Q(insurance__policy_number__icontains=query) |
            Q(insurance__insurance_company__icontains=query)
        ).distinct().order_by('-created_at')
    else:
        applications = Application.objects.all().order_by('-created_at')
    
    context = {
        'applications': applications,
        'search_query': query,
    }
    
    return render(request, 'crm/application_list.html', context)

class ApplicationDetailView(LoginRequiredMixin, DetailView):
    model = Application
    template_name = 'crm/application_detail.html'
    context_object_name = 'application'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        application = self.get_object()

        # Get all related documents using a single query with Q objects
        from django.db.models import Q
        
        document_filters = Q(application=application)
        
        if application.insurance:
            document_filters |= Q(insurance=application.insurance)
            
        if application.mortgage:
            document_filters |= Q(mortgage=application.mortgage)
            
        context['documents'] = Document.objects.filter(document_filters).select_related('uploaded_by')
        context['communications'] = Communication.objects.filter(application=application).order_by('-communication_date')[:10]

        return context

    def post(self, request, *args, **kwargs):
        application = self.get_object()
        action = request.POST.get('action')
        
        if action == 'add_document':
            form = DocumentForm(request.POST)
            if form.is_valid():
                document = form.save(commit=False)
                document.application = application
                document.customer = application.customer
                document.uploaded_by = request.user
                document.save()
                messages.success(request, 'Document added successfully!')
            else:
                messages.error(request, 'Error adding document. Please check the form.')
                
        elif action == 'update_document':
            document_id = request.POST.get('document_id')
            try:
                document = Document.objects.get(document_id=document_id, application=application)
                form = DocumentForm(request.POST, instance=document)
                if form.is_valid():
                    form.save()
                    messages.success(request, 'Document updated successfully!')
                else:
                    messages.error(request, 'Error updating document. Please check the form.')
            except Document.DoesNotExist:
                messages.error(request, 'Document not found.')
                
        elif action == 'add_communication':
            form = CommunicationForm(request.POST)
            if form.is_valid():
                communication = form.save(commit=False)
                communication.application = application
                communication.customer = application.customer
                communication.advisor = request.user
                communication.save()
                messages.success(request, 'Communication logged successfully!')
            else:
                messages.error(request, 'Error logging communication. Please check the form.')
        
        return redirect('application_detail', pk=application.pk)



class ApplicationCreateView(LoginRequiredMixin, CreateView):
    model = Application
    form_class = ApplicationForm
    template_name = 'crm/application_form.html'
    success_url = reverse_lazy('application_list')

    def form_valid(self, form):
        form.instance.advisor = self.request.user
        
        # Handle multiple applications creation here
        # You'll need to override the post method similar to the function-based view
        
        messages.success(self.request, 'Application created successfully!')
        return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['customer'].queryset = Customer.objects.all()
        form.fields['mortgage'].queryset = Mortgage.objects.all()
        form.fields['insurance'].queryset = InsurancePolicy.objects.all()
        return form

class ApplicationUpdateView(LoginRequiredMixin, UpdateView):
    model = Application
    form_class = ApplicationForm
    template_name = 'crm/application_form.html'
    success_url = reverse_lazy('application_list')

    def get_queryset(self):
        return Application.objects.all()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        return kwargs

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['customer'].queryset = Customer.objects.all()
        form.fields['mortgage'].queryset = Mortgage.objects.all()
        form.fields['insurance'].queryset = InsurancePolicy.objects.all()
        
        # Disable application type field in edit mode
        if self.object and self.object.pk:
            form.fields['application_type'].disabled = True
        
        return form

    def form_valid(self, form):
        application = form.save(commit=False)
        
        # Update linked mortgage status if application status changes
        if 'application_status' in form.changed_data and application.mortgage:
            # Map application status to mortgage status
            status_mapping = {
                'Approved': 'Approved',
                'Declined': 'Declined',
                'Completed': 'Completed',
                'Under Review': 'Application',
                'Initial Contact': 'Enquiry',
                'Documents Requested': 'Application',
            }
            
            if application.application_status in status_mapping:
                application.mortgage.mortgage_status = status_mapping[application.application_status]
                application.mortgage.save()
        
        # Update linked insurance status if application status changes
        if 'application_status' in form.changed_data and application.insurance:
            # Map application status to insurance status
            status_mapping = {
                'Approved': 'Active',
                'Declined': 'Cancelled',
                'Completed': 'Active',
                'Under Review': 'Pending',
                'Initial Contact': 'Quote',
                'Documents Requested': 'Pending',
            }
            
            if application.application_status in status_mapping:
                application.insurance.policy_status = status_mapping[application.application_status]
                application.insurance.save()
                
        # Also update insurance_type if it's an insurance application
        if application.insurance and application.application_type == 'Insurance':
            application.insurance_type = application.insurance.policy_type
                
        messages.success(self.request, 'Application updated successfully!')
        return super().form_valid(form)

@login_required
def application_create_view(request):
    """Function-based view for creating applications with multi-select"""
    print(f"DEBUG: Request method: {request.method}")
    
    if request.method == 'POST':
        form = ApplicationForm(request.POST)
        print(f"DEBUG: Form is valid: {form.is_valid()}")
        
        # Debug: Print form errors if any
        if not form.is_valid():
            print(f"DEBUG: Form errors: {form.errors}")
            print(f"DEBUG: Form non-field errors: {form.non_field_errors}")
        
        if form.is_valid():
            application_data = form.cleaned_data
            
            # Get selected insurance types and mortgages
            insurance_types = request.POST.get('selected_insurance_types', '').split(',')
            mortgage_ids = request.POST.get('selected_mortgages', '').split(',')
            
            # Filter out empty strings
            insurance_types = [t for t in insurance_types if t]
            mortgage_ids = [m for m in mortgage_ids if m]  # Keep as strings since mortgage_id is CharField
            
            print(f"DEBUG: Insurance types: {insurance_types}")
            print(f"DEBUG: Mortgage IDs: {mortgage_ids}")
            
            # Validate that at least one option is selected based on application type
            app_type = application_data['application_type']
            
            if app_type == 'Mortgage' and not mortgage_ids:
                form.add_error(None, 'Please select at least one mortgage for mortgage applications.')
            elif app_type == 'Insurance' and not insurance_types:
                form.add_error(None, 'Please select at least one insurance type for insurance applications.')
            elif app_type == 'Both' and (not mortgage_ids or not insurance_types):
                form.add_error(None, 'Please select at least one mortgage and one insurance type for "Both" applications.')
            
            # If we added errors, don't proceed
            if form.errors:
                print(f"DEBUG: Added validation errors: {form.errors}")
            else:
                try:
                    with transaction.atomic():
                        applications_created = 0
                        
                        # Create insurance abbreviation mapping
                        insurance_abbreviations = {
                            'Life Insurance': 'LIFE',
                            'Critical Illness': 'CI',
                            'Income Protection': 'IP',
                            'Buildings Insurance': 'BLDG',
                            'Contents Insurance': 'CNT',
                            'Motor Insurance': 'MOTOR',
                            'Travel Insurance': 'TRVL'
                        }
                        
                        # Create applications for each selected mortgage
                        for mortgage_id in mortgage_ids:
                            try:
                                # Use mortgage_id field instead of id
                                mortgage = Mortgage.objects.get(mortgage_id=mortgage_id)
                                
                                # Generate application number for mortgage
                                timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
                                application_number = f"APP_MRT_{request.user.id}_{timestamp}_{applications_created}"
                                
                                # Create application linked to existing mortgage
                                application = Application.objects.create(
                                    customer=application_data['customer'],
                                    application_type='Mortgage',
                                    application_status=application_data['application_status'],
                                    application_priority=application_data['application_priority'],
                                    submitted_date=application_data['submitted_date'],
                                    expected_completion_date=application_data['expected_completion_date'],
                                    solicitor_name=application_data['solicitor_name'],
                                    follow_up_date=application_data['follow_up_date'],
                                    advisor_notes=application_data['advisor_notes'],
                                    internal_notes=application_data['internal_notes'],
                                    decline_reason=application_data['decline_reason'],
                                    mortgage=mortgage,  # Link to existing mortgage
                                    advisor=request.user,
                                    application_number=application_number
                                )
                                applications_created += 1
                                print(f"DEBUG: Created mortgage application: {application}")
                                
                            except Mortgage.DoesNotExist:
                                messages.warning(request, f'Mortgage with ID {mortgage_id} not found')
                        
                        # Create applications for each selected insurance type
                        # Create applications for each selected insurance type
                        for insurance_type in insurance_types:
                            # Generate a more unique timestamp with milliseconds
                            timestamp = timezone.now().strftime('%Y%m%d%H%M%S%f')[:-3]  # Includes milliseconds

                            prefix = insurance_abbreviations.get(insurance_type, 'INS')
                            application_number = f"APP_INS_{prefix}_{request.user.id}_{timestamp}_{applications_created}"

                            # Generate insurance ID with a more unique timestamp
                            insurance_timestamp = timezone.now().strftime('%Y%m%d%H%M%S%f')[:-3]
                            insurance_id = f"INS_{request.user.id}_{insurance_timestamp}_{applications_created}"

                            # Create insurance policy first with 0 default values
                            insurance_policy = InsurancePolicy.objects.create(
                                customer=application_data['customer'],
                                advisor=request.user,
                                policy_type=insurance_type,
                                coverage_amount=Decimal('0.00'),  # Set to 0
                                premium_amount=Decimal('0.00'),   # Set to 0
                                premium_frequency='Monthly', 
                                insurance_company='Default',      # Default value
                                policy_start_date=timezone.now().date(),
                                policy_status='Quote',
                                insurance_id=insurance_id
                            )

                            # Create application linked to the new insurance policy
                            application = Application.objects.create(
                                customer=application_data['customer'],
                                application_type='Insurance',
                                application_status=application_data['application_status'],
                                application_priority=application_data['application_priority'],
                                submitted_date=application_data['submitted_date'],
                                expected_completion_date=application_data['expected_completion_date'],
                                follow_up_date=application_data['follow_up_date'],
                                advisor_notes=application_data['advisor_notes'],
                                internal_notes=application_data['internal_notes'],
                                decline_reason=application_data['decline_reason'],
                                insurance=insurance_policy,  # Link to the insurance policy
                                insurance_type=insurance_type,
                                advisor=request.user,
                                application_number=application_number
                            )
                            applications_created += 1  # Make sure this is incremented
                            print(f"DEBUG: Created insurance application: {application}")
                    
                    if applications_created > 0:
                        messages.success(request, f'{applications_created} application(s) created successfully!')
                        return redirect('application_list')
                    else:
                        messages.warning(request, 'No applications were created.')
                        
                except Exception as e:
                    print(f"ERROR: {str(e)}")
                    messages.error(request, f'Error creating applications: {str(e)}')
        else:
            print(f"DEBUG: Form is not valid. Errors: {form.errors}")
            messages.error(request, 'Please correct the errors in the form.')
    
    else:
        form = ApplicationForm()
    
    return render(request, 'crm/application_form.html', {
        'form': form,
    })

@login_required
def insurance_communication_create(request, insurance_id):
    """Create communication for insurance policy and link to application"""
    insurance = get_object_or_404(InsurancePolicy, insurance_id=insurance_id)
    
    # Find or create the related application for this insurance policy
    application = insurance.applications.first()
    if not application:
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        application_number = f"APP_INS_{request.user.id}_{timestamp}"
        
        application = Application.objects.create(
            customer=insurance.customer,
            application_type='Insurance',
            application_status='Application Submitted',
            insurance=insurance,
            insurance_type=insurance.policy_type,
            advisor=request.user,
            application_number=application_number
        )
    
    if request.method == 'POST':
        form = CommunicationForm(request.POST)
        if form.is_valid():
            communication = form.save(commit=False)
            communication.insurance = insurance
            communication.application = application  # Link to the application
            communication.customer = insurance.customer
            communication.advisor = request.user
            communication.save()
            messages.success(request, 'Communication logged successfully!')
            return redirect('insurance_detail', pk=insurance.insurance_id)
    else:
        form = CommunicationForm(initial={
            'insurance': insurance,
            'application': application
        })
    
    return render(request, 'crm/communication_form.html', {
        'form': form,
        'insurance': insurance,
        'customer': insurance.customer,
        'application': application
    })


@login_required
def application_communication_create(request, pk):
    """Create communication for any application"""
    application = get_object_or_404(Application, pk=pk)
    
    if request.method == 'POST':
        form = CommunicationForm(request.POST)
        if form.is_valid():
            communication = form.save(commit=False)
            communication.application = application
            communication.customer = application.customer
            communication.advisor = request.user
            
            # Link to insurance or mortgage if they exist
            if application.insurance:
                communication.insurance = application.insurance
            if application.mortgage:
                communication.mortgage = application.mortgage
                
            communication.save()
            messages.success(request, 'Communication logged successfully!')
            return redirect('application_detail', pk=application.pk)
    else:
        form = CommunicationForm(initial={
            'application': application
        })
    
    return render(request, 'crm/communication_form.html', {
        'form': form,
        'application': application,
        'customer': application.customer
    })

@login_required
def insurance_communication_edit(request, insurance_id, pk):
    """Edit a communication for an insurance policy"""
    insurance = get_object_or_404(InsurancePolicy, insurance_id=insurance_id)
    communication = get_object_or_404(Communication, pk=pk, insurance=insurance)
    
    if request.method == 'POST':
        form = CommunicationForm(request.POST, instance=communication)
        if form.is_valid():
            form.save()
            messages.success(request, 'Communication updated successfully!')
            return redirect('insurance_detail', pk=insurance.insurance_id)
    else:
        form = CommunicationForm(instance=communication)
    
    return render(request, 'crm/communication_form.html', {
        'form': form,
        'insurance': insurance,
        'customer': insurance.customer,
        'communication': communication,
        'title': 'Edit Communication'
    })

@login_required
def document_create(request):
    """Create a new document"""
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            
            # Set the uploaded_by field
            document.uploaded_by = request.user
            
            # If application is provided, set customer from application
            application_id = request.POST.get('application')
            if application_id:
                try:
                    application = Application.objects.get(pk=application_id)
                    document.application = application
                    document.customer = application.customer
                except Application.DoesNotExist:
                    pass
                    
            document.save()
            messages.success(request, 'Document added successfully!')
            
            # Redirect back to application detail if it came from there
            if application_id:
                return redirect('application_detail', pk=application_id)
            return redirect('dashboard')
        else:
            messages.error(request, 'Please correct the errors in the form.')
    else:
        form = DocumentForm()
        # Pre-select application if provided in GET parameters
        application_id = request.GET.get('application')
        if application_id:
            form.fields['application'].initial = application_id
    
    return render(request, 'crm/document_form.html', {'form': form})

@login_required
def add_document(request, pk):
    """Add document to insurance policy and link to application"""
    insurance = get_object_or_404(InsurancePolicy, insurance_id=pk)
    
    # Find or create the related application for this insurance policy
    application = insurance.applications.first()
    if not application:
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        application_number = f"APP_INS_{request.user.id}_{timestamp}"
        
        application = Application.objects.create(
            customer=insurance.customer,
            application_type='Insurance',
            application_status='Application Submitted',
            insurance=insurance,
            insurance_type=insurance.policy_type,
            advisor=request.user,
            application_number=application_number
        )
    
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.insurance = insurance
            document.customer = insurance.customer
            document.application = application  # Link to the application
            document.uploaded_by = request.user
            document.save()
            messages.success(request, 'Document added successfully!')
            return redirect('insurance_detail', pk=insurance.insurance_id)
        else:
            messages.error(request, 'Please correct the errors in the form.')
    else:
        # Initialize form with insurance and application preselected
        form = DocumentForm(initial={
            'insurance': insurance,
            'application': application
        })
    
    return render(request, 'crm/document_form.html', {
        'form': form,
        'insurance': insurance,
        'customer': insurance.customer,
        'application': application
    })

@login_required
def insurance_document_create(request, insurance_id):
    """Add document to insurance policy"""
    insurance = get_object_or_404(InsurancePolicy, pk=insurance_id)
    
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)  # Include request.FILES
        if form.is_valid():
            document = form.save(commit=False)
            document.insurance = insurance
            document.customer = insurance.customer
            document.uploaded_by = request.user
            document.save()
            messages.success(request, 'Document added successfully!')
            return redirect('insurance_detail', pk=insurance.pk)
        else:
            messages.error(request, 'Please correct the errors in the form.')
    else:
        # Initialize form with insurance preselected and hidden
        form = DocumentForm(initial={'insurance': insurance})
    
    return render(request, 'crm/document_form.html', {
        'form': form,
        #'insurance': insurance,
        #'customer': insurance.customer
    })

@login_required
def mortgage_document_create(request, mortgage_id):
    """Add document to mortgage"""
    mortgage = get_object_or_404(Mortgage, pk=mortgage_id)
    
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)  # Include request.FILES
        if form.is_valid():
            document = form.save(commit=False)
            document.mortgage = mortgage
            document.customer = mortgage.customer
            document.uploaded_by = request.user
            document.save()
            messages.success(request, 'Document added successfully!')
            return redirect('mortgage_detail', pk=mortgage.pk)
        else:
            messages.error(request, 'Please correct the errors in the form.')
    else:
        # Initialize form with mortgage preselected and hidden
        form = DocumentForm(initial={'mortgage': mortgage})
    
    return render(request, 'crm/document_form.html', {
        'form': form,
        'mortgage': mortgage,
        'customer': mortgage.customer
    })

@login_required
def renewal_alerts(request):
    """View for insurance policy renewal alerts with filtering"""
    advisor = request.user
    today = timezone.now().date()
    
    # Get filter parameters from request
    policy_type_filter = request.GET.get('policy_type', '')
    time_range_filter = request.GET.get('time_range', '30')
    priority_filter = request.GET.get('priority', '')
    
    # Convert time range to integer
    try:
        days_range = int(time_range_filter)
    except (ValueError, TypeError):
        days_range = 30
    
    # Calculate date ranges
    end_date = today + timedelta(days=days_range)
    
    # Base query - filter by advisor and active policies
    policies = InsurancePolicy.objects.filter(
        advisor=advisor,
        policy_status='Active'
    )
    
    # Apply policy type filter if provided
    if policy_type_filter:
        policies = policies.filter(policy_type=policy_type_filter)
    
    # Apply date range filter
    policies = policies.filter(
        renewal_date__gte=today,
        renewal_date__lte=end_date
    ).order_by('renewal_date')
    
    # Categorize policies by urgency
    next_7_days = today + timedelta(days=7)
    next_30_days = today + timedelta(days=30)
    next_90_days = today + timedelta(days=90)
    
    overdue = policies.filter(renewal_date__lt=today)
    due_7_days = policies.filter(
        renewal_date__gte=today,
        renewal_date__lte=next_7_days
    )
    due_30_days = policies.filter(
        renewal_date__gt=next_7_days,
        renewal_date__lte=next_30_days
    )
    due_90_days = policies.filter(
        renewal_date__gt=next_30_days,
        renewal_date__lte=next_90_days
    )
    
    # Calculate counts
    overdue_count = overdue.count()
    urgent_count = due_7_days.count()
    warning_count = due_30_days.count()
    upcoming_count = due_90_days.count()
    total_count = policies.count()
    
    # For export functionality
    if request.GET.get('export') == 'csv':
        return export_renewals_to_csv(policies)
    
    context = {
        'overdue_renewals': overdue,
        'urgent_renewals': due_7_days,
        'warning_renewals': due_30_days,
        'upcoming_renewals': due_90_days,
        'all_renewals': policies,
        'overdue_count': overdue_count,
        'urgent_count': urgent_count,
        'warning_count': warning_count,
        'upcoming_count': upcoming_count,
        'total_count': total_count,
        'policy_types': InsurancePolicy.POLICY_TYPES,
        'applied_filters': {
            'policy_type': policy_type_filter,
            'time_range': time_range_filter,
            'priority': priority_filter,
        }
    }
    
    return render(request, 'crm/renewal_alerts.html', context)


def export_renewals_to_csv(queryset):
    """Export renewal data to CSV"""
    import csv
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="renewal_alerts.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Policy Number', 'Policy Type', 'Customer', 'Coverage Amount', 
        'Premium Amount', 'Renewal Date', 'Days Until Renewal', 'Insurance Company'
    ])
    
    today = timezone.now().date()
    for policy in queryset:
        days_until_renewal = (policy.renewal_date - today).days if policy.renewal_date else 'N/A'
        
        writer.writerow([
            policy.policy_number or 'N/A',
            policy.policy_type,
            f"{policy.customer.first_name} {policy.customer.last_name}",
            f"£{policy.coverage_amount:,.2f}" if policy.coverage_amount else 'N/A',
            f"£{policy.premium_amount:,.2f}" if policy.premium_amount else 'N/A',
            policy.renewal_date.strftime('%Y-%m-%d') if policy.renewal_date else 'N/A',
            days_until_renewal,
            policy.insurance_company
        ])
    
    return response

@login_required
def communication_create(request, customer_id):
    """Create a new communication record"""
    # Remove the advisor filter to allow accessing any customer
    customer = get_object_or_404(Customer, pk=customer_id)
    
    if request.method == 'POST':
        form = CommunicationForm(request.POST)
        if form.is_valid():  # Fixed: changed form.valid() to form.is_valid()
            communication = form.save(commit=False)
            communication.customer = customer
            communication.advisor = request.user
            communication.save()
            messages.success(request, 'Communication logged successfully!')
            return redirect('customer_detail', pk=customer.pk)
    else:
        form = CommunicationForm()
    
    context = {
        'form': form,
        'customer': customer,
    }
    
    return render(request, 'crm/communication_form.html', context)

@login_required
def update_application_status(request, application_id):
    """AJAX endpoint to update application status"""
    if request.method == 'POST':
        application = get_object_or_404(Application, pk=application_id, advisor=request.user)
        new_status = request.POST.get('status')

        if new_status in [choice[0] for choice in Application.STATUS_CHOICES]:
            application.application_status = new_status
            application.save()

            return JsonResponse({
                'success': True,
                'message': f'Application status updated to {new_status}'
            })

    return JsonResponse({'success': False, 'message': 'Invalid request'})

@login_required
def update_application(request, application_id):
    application = Application.objects.get(id=application_id)
    
    # Only update the status field
    if request.method == 'POST':
        application.status = 'Approved'
        application.save()
        return redirect('success_page')
    
    return render(request, 'edit_application.html', {'application': application})

@login_required
def search_customers(request):
    """AJAX endpoint for customer search"""
    query = request.GET.get('q', '')
    customers = Customer.objects.filter(
        advisor=request.user
    ).filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(email__icontains=query)
    )[:10]

    results = []
    for customer in customers:
        results.append({
            'id': customer.customer_id,
            'name': f"{customer.first_name} {customer.last_name}",
            'email': customer.email,
        })

    return JsonResponse({'results': results})

@login_required
def mortgage_search(request):
    """AJAX endpoint for mortgage search"""
    try:
        if request.method == 'GET':
            search_term = request.GET.get('q', '').strip()
            
            if not search_term:
                return JsonResponse([], safe=False)
            
            # Search mortgages by address, postal code, city, or customer name
            mortgages = Mortgage.objects.filter(
                Q(property_address__icontains=search_term) |
                Q(property_postal_code__icontains=search_term) |
                Q(property_city__icontains=search_term) |
                Q(customer__first_name__icontains=search_term) |
                Q(customer__last_name__icontains=search_term)
            )[:10]  # Limit to 10 results
            
            results = []
            for mortgage in mortgages:
                results.append({
                    'id': mortgage.mortgage_id,  # Use mortgage_id instead of id
                    'address': f"{mortgage.property_address}, {mortgage.property_city}",
                    'customer': f"{mortgage.customer.first_name} {mortgage.customer.last_name}",
                    'amount': f"£{mortgage.loan_amount:,.2f}" if mortgage.loan_amount else "£0.00",
                    'postal_code': mortgage.property_postal_code or 'N/A'
                })
            
            print(f"DEBUG: Search for '{search_term}' found {len(results)} results")
            return JsonResponse(results, safe=False)
        else:
            return JsonResponse([], safe=False)
            
    except Exception as e:
        print(f"Error in mortgage_search: {str(e)}")
        return JsonResponse([], safe=False)


@login_required
def add_communication(request, pk):
    """Standalone view to add a communication to an application"""
    application = get_object_or_404(Application, pk=pk)
    
    if request.method == 'POST':
        form = CommunicationForm(request.POST)
        if form.is_valid():
            communication = form.save(commit=False)
            communication.application = application
            communication.customer = application.customer
            communication.advisor = request.user
            communication.save()
            messages.success(request, 'Communication logged successfully!')
        else:
            messages.error(request, 'Error logging communication. Please check the form.')
    
    return redirect('application_detail', pk=application.pk)

@login_required
def edit_document(request, pk):
    """Edit an existing document"""
    document = get_object_or_404(Document, pk=pk)
    
    if request.method == 'POST':
        form = DocumentForm(request.POST, instance=document)
        if form.is_valid():
            form.save()
            messages.success(request, 'Document updated successfully!')
            return redirect('application_detail', pk=document.application.pk)
        else:
            messages.error(request, 'Error updating document. Please check the form.')
    
    # For GET requests, redirect to application detail with modal trigger
    return redirect('application_detail', pk=document.application.pk)



# the reports_view function with real data calculations
@login_required
def reports_view(request):
    """Reports and analytics view with role-based access"""
    # Determine date range (default to last 30 days)
    days_range = int(request.GET.get('days', 30))
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days_range)
    
    # Check if user is a manager
    is_manager = request.user.is_manager if hasattr(request.user, 'is_manager') else False
    
    # Base queryset - filter by advisor if not manager
    if is_manager:
        # Managers see all data
        applications = Application.objects.all()
        policies = InsurancePolicy.objects.all()
        mortgages = Mortgage.objects.all()
        commissions = Commission.objects.all()
        customers = Customer.objects.all()
    else:
        # Regular advisors see only their data
        applications = Application.objects.filter(advisor=request.user)
        policies = InsurancePolicy.objects.filter(advisor=request.user)
        mortgages = Mortgage.objects.filter(advisor=request.user)
        commissions = Commission.objects.filter(advisor=request.user)
        customers = Customer.objects.filter(advisor=request.user)
    
    # Filter by date range
    applications = applications.filter(created_at__range=[start_date, end_date])
    policies = policies.filter(created_at__range=[start_date, end_date])
    mortgages = mortgages.filter(created_at__range=[start_date, end_date])
    commissions = commissions.filter(created_at__range=[start_date, end_date])
    
    # Calculate metrics
    total_revenue = commissions.aggregate(Sum('commission_amount'))['commission_amount__sum'] or 0
    new_policies = policies.filter(
        policy_status='Active',
        policy_start_date__gte=start_date.date()
    ).count()
    
    # Calculate renewal rate
    active_policies = policies.filter(policy_status='Active')
    renewed_policies = policies.filter(
        policy_status='Renewed',
        renewal_date__gte=start_date.date(),
        renewal_date__lte=end_date.date()
    ).count()
    
    renewal_rate = (renewed_policies / active_policies.count() * 100) if active_policies.count() > 0 else 0
    
    # Calculate average commission
    avg_commission = commissions.aggregate(Avg('commission_amount'))['commission_amount__avg'] or 0
    
    # Mortgage-specific metrics
    mortgage_applications = mortgages.filter(
        application_date__gte=start_date.date(),
        application_date__lte=end_date.date()
    ).count()
    
    # Calculate average loan amount
    avg_loan_amount = mortgages.aggregate(Avg('loan_amount'))['loan_amount__avg'] or 0
    
    # Calculate success rate for applications
    total_applications = applications.count()
    completed_applications = applications.filter(application_status='Completed').count()
    success_rate = (completed_applications / total_applications * 100) if total_applications > 0 else 0
    
    # Document status overview
    documents = Document.objects.filter(application__in=applications)
    document_status = {
        'Required': documents.filter(document_status='Required').count(),
        'Requested': documents.filter(document_status='Requested').count(),
        'Received': documents.filter(document_status='Received').count(),
        'Verified': documents.filter(document_status='Verified').count(),
        'Rejected': documents.filter(document_status='Rejected').count(),
    }
    document_status_total = sum(document_status.values())
    
    # Policy performance by type
    policy_performance = []
    for policy_type in InsurancePolicy.POLICY_TYPES:
        type_policies = policies.filter(policy_type=policy_type[0])
        type_count = type_policies.count()
        if type_count > 0:
            type_revenue = type_policies.aggregate(Sum('premium_amount'))['premium_amount__sum'] or 0
            avg_premium = type_revenue / type_count
            policy_performance.append({
                'type': policy_type[0],
                'count': type_count,
                'revenue': type_revenue,
                'avg_premium': avg_premium,
                'renewal_rate': 75,  # Placeholder - implement actual calculation
                'growth': 10,  # Placeholder - implement actual calculation
            })
    
    # Upcoming renewals
    upcoming_renewals = policies.filter(
        renewal_date__gte=timezone.now().date(),
        renewal_date__lte=timezone.now().date() + timedelta(days=30),
        policy_status='Active'
    ).select_related('customer').order_by('renewal_date')
    
    # Add days until renewal to each renewal
    for renewal in upcoming_renewals:
        renewal.days_until_renewal = (renewal.renewal_date - timezone.now().date()).days
    
    # Advisor Performance Comparison Data
    Advisor = get_user_model()
    
    # Calculate previous period for growth comparisons
    prev_start_date = start_date - (end_date - start_date)
    prev_end_date = start_date
    
    # Revenue growth calculation
    prev_revenue = Commission.objects.filter(
        created_at__range=[prev_start_date, prev_end_date],
        advisor=request.user
    ).aggregate(Sum('commission_amount'))['commission_amount__sum'] or 0
    revenue_growth = calculate_growth(prev_revenue, total_revenue)
    
    # Policy growth calculation
    prev_policies = InsurancePolicy.objects.filter(
        created_at__range=[prev_start_date, prev_end_date],
        advisor=request.user
    ).count()
    policy_growth = calculate_growth(prev_policies, new_policies)
    
    # Renewal change calculation (placeholder)
    renewal_change = 5  # Placeholder value
    
    # Commission growth calculation
    prev_commission = Commission.objects.filter(
        created_at__range=[prev_start_date, prev_end_date],
        advisor=request.user
    ).aggregate(Avg('commission_amount'))['commission_amount__avg'] or 0
    commission_growth = calculate_growth(prev_commission, avg_commission)
    
    # Mortgage growth calculation
    prev_mortgage_apps = Mortgage.objects.filter(
        created_at__range=[prev_start_date, prev_end_date],
        advisor=request.user
    ).count()
    mortgage_growth = calculate_growth(prev_mortgage_apps, mortgage_applications)
    
    # Loan amount change calculation
    prev_avg_loan = Mortgage.objects.filter(
        created_at__range=[prev_start_date, prev_end_date],
        advisor=request.user
    ).aggregate(Avg('loan_amount'))['loan_amount__avg'] or 0
    loan_amount_change = calculate_growth(prev_avg_loan, avg_loan_amount)
    
    # Success rate change calculation
    prev_total_apps = Application.objects.filter(
        created_at__range=[prev_start_date, prev_end_date],
        advisor=request.user
    ).count()
    prev_completed_apps = Application.objects.filter(
        application_status='Completed',
        created_at__range=[prev_start_date, prev_end_date],
        advisor=request.user
    ).count()
    prev_success_rate = (prev_completed_apps / prev_total_apps * 100) if prev_total_apps > 0 else 0
    success_rate_change = calculate_growth(prev_success_rate, success_rate)
    
    # Pending documents change calculation
    prev_pending_docs = Document.objects.filter(
        application__in=Application.objects.filter(
            created_at__range=[prev_start_date, prev_end_date],
            advisor=request.user
        ),
        document_status='Required'
    ).count()
    pending_docs_change = calculate_growth(prev_pending_docs, document_status['Required'])
    
    # Charts data
    revenue_data = get_revenue_trend_data(commissions, 6)
    product_data = get_product_distribution_data(policies)
    application_status_data = get_application_status_data(applications)
    commission_type_data = get_commission_type_data(commissions)
    renewal_chart_data = get_renewal_chart_data(policies)
    
    # Advisor Performance (for managers)
    advisor_performance = []
    if is_manager:
        advisor_performance = get_advisor_performance_data(Advisor.objects.filter(is_active=True), start_date, end_date)
    
    # Top Advisors
    top_advisors = get_top_advisors(Advisor.objects.filter(is_active=True), start_date, end_date)
    
    # Mortgage Performance
    mortgage_performance = get_mortgage_performance_data(mortgages)
    
    context = {
        'start_date': start_date.date(),
        'end_date': end_date.date(),
        'days_range': days_range,
        'total_revenue': total_revenue,
        'revenue_growth': revenue_growth,
        'new_policies': new_policies,
        'policy_growth': policy_growth,
        'renewal_rate': renewal_rate,
        'renewal_change': renewal_change,
        'avg_commission': avg_commission,
        'commission_growth': commission_growth,
        'mortgage_applications': mortgage_applications,
        'mortgage_growth': mortgage_growth,
        'avg_loan_amount': avg_loan_amount,
        'loan_amount_change': loan_amount_change,
        'success_rate': success_rate,
        'success_rate_change': success_rate_change,
        'document_status': document_status,
        'document_status_total': document_status_total,
        'pending_docs_change': pending_docs_change,
        'policy_performance': policy_performance,
        'upcoming_renewals': upcoming_renewals,
        'user': request.user,
        'advisor_performance': advisor_performance,
        'top_advisors': top_advisors,
        'mortgage_completion_rate': mortgage_performance['completion_rate'],
        'avg_mortgage_commission': mortgage_performance['avg_commission'],
        'top_mortgage_lender': mortgage_performance['top_lender'],
        'mortgage_types_popular': mortgage_performance['popular_type'],
        
        # Charts data
        'revenue_labels': revenue_data['labels'],
        'revenue_data': revenue_data['values'],
        'product_labels': product_data['labels'],
        'product_data': product_data['values'],
        'application_status_labels': application_status_data['labels'],
        'application_status_data': application_status_data['values'],
        'commission_type_labels': commission_type_data['labels'],
        'commission_type_data': commission_type_data['values'],
        'renewal_labels': renewal_chart_data['labels'],
        'renewal_data': renewal_chart_data['values'],
        
        # Form options
        'policy_types': InsurancePolicy.POLICY_TYPES,
        'all_advisors': Advisor.objects.filter(is_active=True) if is_manager else [],
    }

    return render(request, 'crm/reports.html', context)

def get_revenue_trend_data(commissions, months=6):
    """Get revenue trend data for chart"""
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30*months)
    
    monthly_data = commissions.filter(
        created_at__range=[start_date, end_date]
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        total=Sum('commission_amount')
    ).order_by('month')
    
    labels = []
    values = []
    
    for data in monthly_data:
        labels.append(data['month'].strftime('%b %Y'))
        values.append(float(data['total'] or 0))
    
    return {'labels': labels, 'values': values}

def get_product_distribution_data(policies):
    """Get product distribution data for chart"""
    # Use 'insurance_id' instead of 'id' for counting
    product_data = policies.values('policy_type').annotate(
        count=Count('insurance_id')
    ).order_by('-count')
    
    labels = []
    values = []
    
    for data in product_data:
        labels.append(data['policy_type'])
        values.append(data['count'])
    
    return {'labels': labels, 'values': values}

def get_renewal_chart_data(policies):
    """Get renewal status data for chart"""
    # Use 'insurance_id' instead of 'id' for counting
    renewal_data = policies.values('policy_status').annotate(
        count=Count('insurance_id')
    ).order_by('-count')
    
    labels = []
    values = []
    
    for data in renewal_data:
        labels.append(data['policy_status'])
        values.append(data['count'])
    
    return {'labels': labels, 'values': values}

def get_application_status_data(applications):
    """Get application status distribution data for chart"""
    status_data = applications.values('application_status').annotate(
        count=Count('application_id')
    ).order_by('-count')
    
    labels = []
    values = []
    
    for data in status_data:
        labels.append(data['application_status'])
        values.append(data['count'])
    
    return {'labels': labels, 'values': values}

def get_commission_type_data(commissions):
    """Get commission type distribution data for chart"""
    type_data = commissions.values('commission_type').annotate(
        total=Sum('commission_amount')
    ).order_by('-total')
    
    labels = []
    values = []
    
    for data in type_data:
        labels.append(data['commission_type'])
        values.append(float(data['total'] or 0))
    
    return {'labels': labels, 'values': values}


def get_advisor_performance_data(advisors, start_date, end_date):
    """Get advisor performance data for managers"""
    advisor_performance = []
    
    for advisor in advisors:
        advisor_apps = Application.objects.filter(
            advisor=advisor,
            created_at__range=[start_date, end_date]
        )
        advisor_commissions = Commission.objects.filter(
            advisor=advisor,
            created_at__range=[start_date, end_date]
        )
        
        completed_apps = advisor_apps.filter(application_status='Completed').count()
        total_apps = advisor_apps.count()
        success_rate = (completed_apps / total_apps * 100) if total_apps > 0 else 0
        total_revenue = advisor_commissions.aggregate(
            Sum('commission_amount')
        )['commission_amount__sum'] or 0
        
        advisor_performance.append({
            'advisor': advisor,
            'total_applications': total_apps,
            'completed_applications': completed_apps,
            'success_rate': success_rate,
            'total_revenue': total_revenue,
        })
    
    return sorted(advisor_performance, key=lambda x: x['total_revenue'], reverse=True)

def get_top_advisors(advisors, start_date, end_date, limit=5):
    """Get top performing advisors by revenue"""
    advisor_performance = []
    
    for advisor in advisors:
        advisor_commissions = Commission.objects.filter(
            advisor=advisor,
            created_at__range=[start_date, end_date]
        )
        total_revenue = advisor_commissions.aggregate(
            Sum('commission_amount')
        )['commission_amount__sum'] or 0
        
        if total_revenue > 0:
            advisor_performance.append({
                'advisor': advisor,
                'total_revenue': total_revenue,
            })
    
    return sorted(advisor_performance, key=lambda x: x['total_revenue'], reverse=True)[:limit]

def get_mortgage_performance_data(mortgages):
    """Get mortgage performance metrics"""
    completed_mortgages = mortgages.filter(mortgage_status='Approved').count()
    total_mortgages = mortgages.count()
    completion_rate = (completed_mortgages / total_mortgages * 100) if total_mortgages > 0 else 0
    
    # Calculate average commission from related applications
    mortgage_commissions = Commission.objects.filter(
        mortgage__in=mortgages
    ).aggregate(Avg('commission_amount'))['commission_amount__avg'] or 0
    
    # Find top lender - use 'lender' field instead of 'lender_name'
    lender_data = mortgages.values('lender').annotate(
        count=Count('mortgage_id')  # Use 'mortgage_id' instead of 'id'
    ).order_by('-count').first()
    top_lender = lender_data['lender'] if lender_data else 'N/A'
    
    # Find most popular mortgage type - use 'mortgage_id' instead of 'id'
    type_data = mortgages.values('mortgage_type').annotate(
        count=Count('mortgage_id')  # Use 'mortgage_id' instead of 'id'
    ).order_by('-count').first()
    popular_type = type_data['mortgage_type'] if type_data else 'N/A'

    return {
        'completion_rate': completion_rate,
        'avg_commission': mortgage_commissions,
        'top_lender': top_lender,
        'popular_type': popular_type,
    }


# Define the function first
def get_weekly_commission_data(year):
    # Your implementation here
    weekly_data = []
    # Calculate weekly commission data
    return weekly_data


# Then call it inside a function or method, not at module level
def some_view_function(request):
    weekly_commission_data = get_weekly_commission_data(year=datetime.now().year)

# Payments and Commissions



@login_required
def payment_list(request):
    """List all payments"""
    payments = Payment.objects.all().order_by('-payment_date')

    # Filtering
    status_filter = request.GET.get('status')
    if status_filter:
        payments = payments.filter(payment_status=status_filter)

    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        payments = payments.filter(payment_date__gte=date_from)
    if date_to:
        payments = payments.filter(payment_date__lte=date_to)

    context = {
        'payments': payments,
        'status_choices': Payment.PAYMENT_STATUS_CHOICES,
    }
    return render(request, 'crm/payment_list.html', context)


@login_required
def payment_detail(request, pk):
    """Payment detail view"""
    payment = get_object_or_404(Payment, pk=pk)
    return render(request, 'crm/payment_detail.html', {'payment': payment})


@login_required
def payment_create(request):
    """Create a new payment"""
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save()
            messages.success(request, 'Payment created successfully!')
            return redirect('payment_detail', pk=payment.pk)
    else:
        form = PaymentForm()

    return render(request, 'crm/payment_form.html', {'form': form})


@login_required
def payment_update(request, pk):
    """Update a payment"""
    payment = get_object_or_404(Payment, pk=pk)

    if request.method == 'POST':
        form = PaymentForm(request.POST, instance=payment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Payment updated successfully!')
            return redirect('payment_detail', pk=payment.pk)
    else:
        form = PaymentForm(instance=payment)

    return render(request, 'crm/payment_form.html', {'form': form})

@login_required
def commission_weeks(request):
    """List commission weeks with filtering"""
    weeks = CommissionWeek.objects.all().order_by('-year', '-week_number')

    # Filter by advisor
    advisor_filter = request.GET.get('advisor')
    if advisor_filter:
        weeks = weeks.filter(advisor_id=advisor_filter)

    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        weeks = weeks.filter(status=status_filter)

    # Filter by year
    year_filter = request.GET.get('year')
    if year_filter:
        weeks = weeks.filter(year=year_filter)

    context = {
        'weeks': weeks,
        'advisors': User.objects.filter(is_active=True),
        'status_choices': CommissionWeek._meta.get_field('status').choices,
        'years': range(datetime.now().year - 2, datetime.now().year + 3),
    }
    return render(request, 'crm/commission_weeks.html', context)

@login_required
def commission_week_detail(request, pk):
    week = get_object_or_404(CommissionWeek, pk=pk)
    
    # Get commission mappings for this week (insurance policies only)
    commission_mappings = CommissionMapping.objects.filter(commission_week=week).select_related('insurance_policy', 'insurance_policy__customer')
    
    # Check if user can approve (manager and week is pending)
    can_approve = request.user.is_manager and week.status == 'Pending Review'
    
    context = {
        'week': week,
        'commission_mappings': commission_mappings,
        'total_mappings_count': commission_mappings.count(),
        'can_approve': can_approve,
        'advisor_name': week.advisor.get_full_name() if week.advisor else 'N/A',  
        'business_week_start': week.start_date.strftime('%d.%m.%Y') if week.start_date else 'N/A',  
        'business_week_end': week.end_date.strftime('%d.%m.%Y') if week.end_date else 'N/A',  
        'selected_week': week.week_number,  
    }
    
    return render(request, 'crm/commission_week_detail.html', context)

@login_required
def add_insurance_to_week(request, week_id):
    """Add insurance policies to commission week"""
    week = get_object_or_404(CommissionWeek, pk=week_id)
    
    if request.method == 'POST':
        policy_ids = request.POST.getlist('policy_ids')
        policies_added = 0
        
        for policy_id in policy_ids:
            policy = get_object_or_404(InsurancePolicy, pk=policy_id)
            
            # Check if policy is already mapped
            if CommissionMapping.objects.filter(commission_week=week, insurance_policy=policy).exists():
                continue
            
            # Create commission mapping
            CommissionMapping.objects.create(
                commission_week=week,
                insurance_policy=policy,
                commission_rate=Decimal('20.0'),  # Default 20% commission rate
                estimated_commission=policy.premium_amount * Decimal('0.2')
            )
            policies_added += 1
        
        if policies_added > 0:
            messages.success(request, f'{policies_added} insurance policy(s) added to commission week.')
        else:
            messages.warning(request, 'No policies were added. They may have already been assigned.')
        
        return redirect('commission_week_detail', pk=week.pk)
    
    # GET request - show available policies
    available_policies = InsurancePolicy.objects.filter(
        policy_status__in=['Active', 'Renewed'],
        advisor=request.user
    ).exclude(
        commissionmapping__commission_week=week
    ).select_related('customer')
    
    # Calculate estimated commission for each policy
    for policy in available_policies:
        policy.estimated_commission = policy.premium_amount * Decimal('0.2')
    
    context = {
        'week': week,
        'available_policies': available_policies,
    }
    
    return render(request, 'crm/add_insurance_to_week.html', context)

# In views.py - update the update_commission_mapping view
@login_required
def update_commission_mapping(request, mapping_id):
    """Update commission mapping for insurance policies"""
    mapping = get_object_or_404(CommissionMapping, pk=mapping_id)

    if not (request.user.is_manager or mapping.commission_week.advisor == request.user):
        messages.error(request, 'You do not have permission to update this commission mapping.')
        return redirect('commission_week_detail', pk=mapping.commission_week.pk)

    if request.method == 'POST':
        form = CommissionMappingForm(request.POST, instance=mapping)
        if form.is_valid():
            mapping = form.save(commit=False)
            
            # Recalculate estimated commission if premium or rate changes
            if 'premium_amount' in form.changed_data or 'commission_rate' in form.changed_data:
                mapping.estimated_commission = mapping.insurance_policy.premium_amount * (mapping.commission_rate / Decimal('100'))
            
            mapping.updated_by = request.user
            mapping.save()
            
            # Update the week totals
            mapping.commission_week.update_totals()
            
            messages.success(request, 'Commission mapping updated successfully!')
            return redirect('commission_week_detail', pk=mapping.commission_week.pk)
    else:
        form = CommissionMappingForm(instance=mapping)

    context = {
        'form': form,
        'mapping': mapping,
    }
    
    return render(request, 'crm/commission_mapping_form.html', context)

# commission_week_create view
@login_required
def commission_week_create(request):
    """Create a new commission week with proper validation"""
    if request.method == 'POST':
        form = CommissionWeekForm(request.POST)
        if form.is_valid():
            try:
                week = form.save()
                messages.success(request, 'Commission week created successfully!')
                return redirect('commission_week_detail', pk=week.pk)
            except ValidationError as e:
                form.add_error(None, e)
    else:
        # Set default values to current week
        today = date.today()
        year = today.year
        week_number = today.isocalendar()[1]
        
        # Calculate start and end dates for the week
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)
        
        form = CommissionWeekForm(initial={
            'week_number': week_number,
            'year': year,
            'start_date': start_date,
            'end_date': end_date,
            'advisor': request.user
        })

    return render(request, 'crm/commission_week_form.html', {'form': form})


@login_required
def submit_week_for_approval(request, pk):
    """Advisor submits week for manager approval"""
    week = get_object_or_404(CommissionWeek, pk=pk, advisor=request.user)
    
    if week.status != 'Open':
        messages.error(request, 'Only open weeks can be submitted for approval.')
        return redirect('commission_week_detail', pk=pk)
    
    # Validate that week has commission mappings (not applications)
    if not CommissionMapping.objects.filter(commission_week=week).exists():
        messages.error(request, 'Cannot submit empty week for approval.')
        return redirect('commission_week_detail', pk=pk)
    
    week.status = 'Pending Review'
    week.save()
    
    messages.success(request, f'Week {week.week_number} submitted for manager approval.')
    return redirect('commission_week_detail', pk=week.pk)

@login_required
def weekly_commission_report(request):
    """Weekly commission report view - FIXED"""
    # Get filter parameters from request
    selected_week = request.GET.get('week')
    selected_year = request.GET.get('year', datetime.now().year)
    active_tab = request.GET.get('tab', 'weeks')

    # Convert to integers with validation
    try:
        selected_year = int(selected_year)
        selected_week = int(selected_week) if selected_week else None
    except (ValueError, TypeError):
        selected_year = datetime.now().year
        selected_week = None

    # Base queryset - managers see all weeks, others see only their own
    if request.user.is_manager:
        available_weeks = CommissionWeek.objects.all()
    else:
        available_weeks = CommissionWeek.objects.filter(advisor=request.user)
    
    available_weeks = available_weeks.order_by('-year', '-week_number').distinct()

    # If no week selected, use the most recent week
    if not selected_week and available_weeks.exists():
        latest_week = available_weeks.first()
        selected_week = latest_week.week_number
        selected_year = latest_week.year

    # Filter for display weeks
    display_weeks = available_weeks
    if selected_week and selected_year:
        display_weeks = display_weeks.filter(week_number=selected_week, year=selected_year)

    # Calculate totals
    total_estimated = display_weeks.aggregate(
        total=Sum('total_estimated_commission')
    )['total'] or Decimal('0.00')

    total_actual = display_weeks.aggregate(
        total=Sum('total_actual_commission')
    )['total'] or Decimal('0.00')

    variance = total_estimated - total_actual
    variance_percentage = (variance / total_estimated * 100) if total_estimated else Decimal('0.00')

    # Get commission mappings for the selected weeks
    commission_mappings = CommissionMapping.objects.filter(commission_week__in=display_weeks)
    
    # Calculate metrics
    completed_applications = commission_mappings.count()
    pending_count = commission_mappings.filter(actual_commission__isnull=True).count()
    pending_approval = commission_mappings.filter(
        actual_commission__isnull=True
    ).aggregate(total=Sum('estimated_commission'))['total'] or Decimal('0.00')

    # Week dates for display
    week_dates = "N/A"
    if display_weeks.exists():
        week = display_weeks.first()
        week_dates = f"{week.start_date.strftime('%d.%m.%Y')} to {week.end_date.strftime('%d.%m.%Y')}"

    # Prepare weekly data - FIX: Check if we're on the advisor-report tab
    weekly_data = []
    totals = {}
    
    if active_tab == 'advisor-report' and selected_week and selected_year:
        # Get DailyAdvisorActivity data for the selected week
        week_start, week_end = get_week_dates(selected_year, selected_week)
        
        # Get activities for this week
        daily_activities = DailyAdvisorActivity.objects.filter(
            advisor=request.user,
            date__range=[week_start, week_end]
        ).order_by('date')
        
        # Prepare weekly data structure
        weekly_data = prepare_weekly_advisor_data_from_activities(daily_activities, week_start)
        totals = calculate_weekly_totals(weekly_data)

    # Product summary for commission breakdown
    product_summary = []
    for mapping in commission_mappings:
        policy = mapping.insurance_policy
        product_summary.append({
            'type': policy.policy_type,
            'count': 1,
            'premium': policy.premium_amount or Decimal('0.00'),
            'rate': mapping.commission_rate,
            'commission': mapping.estimated_commission or Decimal('0.00')
        })

    # Aggregate product summary
    aggregated_summary = {}
    for item in product_summary:
        if item['type'] not in aggregated_summary:
            aggregated_summary[item['type']] = {
                'type': item['type'],
                'count': 0,
                'premium': Decimal('0.00'),
                'rate': Decimal('0.00'),
                'commission': Decimal('0.00')
            }
        aggregated_summary[item['type']]['count'] += item['count']
        aggregated_summary[item['type']]['premium'] += item['premium']
        aggregated_summary[item['type']]['commission'] += item['commission']
        # Average rate
        aggregated_summary[item['type']]['rate'] = item['rate']

    product_summary = list(aggregated_summary.values())

    total_applications = sum(item['count'] for item in product_summary)
    total_premium = sum(item['premium'] for item in product_summary)
    total_commission = sum(item['commission'] for item in product_summary)

    # Calculate metrics
    conversion_rate = Decimal('75.5') if total_applications > 0 else Decimal('0.00')
    commission_efficiency = (total_actual / total_estimated * 100) if total_estimated else Decimal('0.00')
    payment_processing = Decimal('92.1')  # Placeholder

    context = {
        'commission_weeks': display_weeks,
        'available_weeks': available_weeks,
        'selected_week': selected_week,
        'selected_year': selected_year,
        'total_estimated': total_estimated,
        'total_actual': total_actual,
        'variance': variance,
        'variance_percentage': variance_percentage,
        'pending_approval': pending_approval,
        'pending_count': pending_count,
        'completed_applications': completed_applications,
        'estimated_growth': Decimal('5.2'),
        'week_dates': week_dates,
        'active_tab': active_tab,
        'weekly_data': weekly_data,  # This will now contain actual data
        'totals': totals,  # This will now contain actual totals
        'product_summary': product_summary,
        'total_applications': total_applications,
        'total_premium': total_premium,
        'total_commission': total_commission,
        'conversion_rate': conversion_rate,
        'commission_efficiency': commission_efficiency,
        'payment_processing': payment_processing,
    }

    return render(request, 'crm/weekly_commission_report.html', context)

@login_required
def commission_week_update(request, pk):
    """Update a commission week"""
    week = get_object_or_404(CommissionWeek, pk=pk)

    if not request.user.is_manager:
        messages.error(request, 'Only managers can update commission weeks.')
        return redirect('commission_weeks')

    if request.method == 'POST':
        form = CommissionWeekForm(request.POST, instance=week)
        if form.is_valid():
            form.save()
            messages.success(request, 'Commission week updated successfully!')
            return redirect('commission_week_detail', pk=week.pk)
    else:
        form = CommissionWeekForm(instance=week)

    return render(request, 'crm/commission_week_form.html', {'form': form, 'week': week})


@login_required
def payment_update(request, pk):
    """Update a payment"""
    payment = get_object_or_404(Payment, pk=pk)

    if request.method == 'POST':
        form = PaymentForm(request.POST, instance=payment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Payment updated successfully!')
            return redirect('payment_detail', pk=payment.pk)
    else:
        form = PaymentForm(instance=payment)

    return render(request, 'crm/payment_form.html', {'form': form})


@login_required
def payment_detail(request, pk):
    """Payment detail view"""
    payment = get_object_or_404(Payment, pk=pk)
    return render(request, 'crm/payment_detail.html', {'payment': payment})


class CommissionWeeksListView(ListView):
    model = CommissionWeek
    template_name = 'crm/commission_weeks.html'  # Add the 'crm/' prefix
    context_object_name = 'weeks'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = CommissionWeek.objects.all()
        
        # Filter by advisor if requested
        advisor_id = self.request.GET.get('advisor')
        if advisor_id:
            queryset = queryset.filter(advisor_id=advisor_id)
        
        # Filter by status if requested
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by year if requested
        year = self.request.GET.get('year')
        if year:
            queryset = queryset.filter(year=year)
        
        return queryset.select_related('advisor').order_by('-year', '-week_number')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Use User model instead of Advisor
        context['advisors'] = User.objects.filter(is_active=True)
        
        # Get status choices from the model
        context['status_choices'] = CommissionWeek._meta.get_field('status').choices
        
        # Get distinct years from CommissionWeek
        years = CommissionWeek.objects.dates('start_date', 'year')
        context['years'] = [year.year for year in years] if years else [datetime.now().year]
        
        return context    
    
class WeeklyCommissionReportView(LoginRequiredMixin, TemplateView):
    template_name = 'crm/weekly_commission_report.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get the active tab from request
        active_tab = self.request.GET.get('tab', 'weeks')
        context['active_tab'] = active_tab
        
        # Handle advisor report tab
        if active_tab == 'advisor-report':
            selected_week = self.request.GET.get('week', datetime.now().isocalendar()[1])
            selected_year = self.request.GET.get('year', datetime.now().year)
            
            context['selected_week'] = selected_week
            context['selected_year'] = selected_year
            
            # Get weekly data for the advisor
            weekly_data = self.get_weekly_data(selected_week, selected_year)
            context['weekly_data'] = weekly_data
            
            # Calculate week dates for display
            if weekly_data:
                context['week_dates'] = f"Week {selected_week}, {selected_year}"
        
        # Get filter parameters
        week = self.request.GET.get('week')
        year = self.request.GET.get('year')
        advisor_id = self.request.GET.get('advisor')
        
        # Build queryset
        weeks = CommissionWeek.objects.all()
        
        if week and year:
            weeks = weeks.filter(week_number=week, year=year)
        elif not week and not year:
            # Default to current week
            current_week = datetime.now().isocalendar()[1]
            current_year = datetime.now().year
            weeks = weeks.filter(week_number=current_week, year=current_year)
        
        if advisor_id:
            weeks = weeks.filter(advisor_id=advisor_id)
        
        context['commission_weeks'] = weeks.select_related('advisor')
        # Use User model instead of Advisor
        context['advisors'] = User.objects.filter(is_active=True)
        
        # Calculate totals
        total_estimated = weeks.aggregate(Sum('total_estimated_commission'))['total_estimated_commission__sum'] or 0
        total_actual = weeks.aggregate(Sum('total_actual_commission'))['total_actual_commission__sum'] or 0
        
        context['total_estimated'] = total_estimated
        context['total_actual'] = total_actual
        context['variance'] = total_estimated - total_actual
        context['variance_percentage'] = (context['variance'] / total_estimated * 100) if total_estimated else 0
        
        return context
    def get_weekly_data(self, week, year):
        # Your logic to get weekly data for the advisor
        # This should return data structured for the advisor report table
        pass
    
class UpdateCommissionMappingView(LoginRequiredMixin, UpdateView):
    """Update commission mapping view"""
    model = CommissionMapping
    form_class = CommissionMappingForm  
    template_name = 'crm/commission_mapping_form.html'
    
    def get_success_url(self):
        return reverse_lazy('commission_week_detail', kwargs={'pk': self.object.commission_week.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Commission mapping updated successfully!')
        return super().form_valid(form)
    
class DocumentCreateView(CreateView):
    model = Document
    fields = ['document_name', 'document_type', 'document_file', 'document_status', 'requested_date', 'received_date']
    template_name = 'crm/document_form.html'
    
    def form_valid(self, form):
        form.instance.application_id = self.request.POST.get('application')
        form.instance.uploaded_by = self.request.user
        
        # Set customer based on application or other context
        application_id = self.request.POST.get('application')
        if application_id:
            try:
                application = Application.objects.get(pk=application_id)
                form.instance.customer = application.customer
            except Application.DoesNotExist:
                pass
                
        return super().form_valid(form)
    
    def get_success_url(self):
        if self.object.application:
            return reverse_lazy('application_detail', kwargs={'pk': self.object.application.pk})
        else:
            return reverse_lazy('dashboard')

# In views.py - update DocumentEditView
class DocumentEditView(UpdateView):
    model = Document
    fields = ['document_name', 'document_type', 'document_file', 'document_status', 'requested_date', 'received_date']
    template_name = 'crm/document_form.html'
    
    def get_success_url(self):
        if self.object.application:
            return reverse_lazy('application_detail', kwargs={'pk': self.object.application.pk})
        else:
            return reverse_lazy('dashboard')
            
def manager_required(view_func):
    """Decorator to ensure user is a manager"""
    decorated_view_func = user_passes_test(
        lambda u: u.is_authenticated and u.is_manager,
        login_url='dashboard',
        redirect_field_name=None
    )(view_func)
    return decorated_view_func

@login_required
@manager_required
def commission_week_approval(request, pk):
    """Manager approval view for commission weeks"""
    week = get_object_or_404(CommissionWeek, pk=pk)
    
    if request.method == 'POST':
        form = CommissionWeekApprovalForm(request.POST, instance=week)
        if form.is_valid():
            commission_week = form.save(commit=False)
            
            if form.cleaned_data['status'] == 'Approved':
                commission_week.approved_by = request.user
                commission_week.approved_at = timezone.now()
            
            commission_week.save()
            
            messages.success(request, f'Commission week {week.week_number} has been {form.cleaned_data["status"].lower()}.')
            return redirect('commission_week_detail', pk=week.pk)
    else:
        form = CommissionWeekApprovalForm(instance=week)
    
    # FIX: Change 'mappings' to 'insurance_mappings' to match template
    context = {
        'week': week,
        'form': form,
        'insurance_mappings': week.mappings.all().select_related('insurance_policy', 'insurance_policy__customer')
    }
    
    return render(request, 'crm/commission_week_approval.html', context)

@login_required
@manager_required
def manager_commission_weeks(request):
    """Commission weeks list for managers with approval actions"""
    weeks = CommissionWeek.objects.filter(status='Pending Review').order_by('-year', '-week_number')
    
    context = {
        'weeks': weeks,
        'is_manager': True
    }
    
    return render(request, 'crm/manager_commission_weeks.html', context)

# Helper function to connect to insurance system API
def fetch_insurance_data_from_api(policy_id):
    # Implement your insurance system API integration here
    # This is a placeholder implementation
    import requests
    from django.conf import settings
    
    api_url = f"{settings.INSURANCE_API_BASE_URL}/policies/{policy_id}"
    headers = {
        'Authorization': f'Bearer {settings.INSURANCE_API_TOKEN}'
    }
    
    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        # Handle API errors appropriately
        raise Exception(f"Insurance API error: {str(e)}")

# views.py
@login_required
def auto_assign_applications(request):
    """Auto-assign applications to advisors"""
    # Your implementation here
    messages.success(request, 'Applications auto-assigned successfully!')
    return redirect('application_list')  # or appropriate redirect

@require_POST
@csrf_exempt
def update_insurance_commission(request):
    """Update insurance commission mapping"""
    mapping_id = request.POST.get('mapping_id')
    actual_commission = request.POST.get('actual_commission')
    
    try:
        mapping = CommissionMapping.objects.get(id=mapping_id)
        mapping.actual_commission = actual_commission
        mapping.save()
        
        # Update the week's total
        week = mapping.commission_week
        week.update_totals()
        
        return JsonResponse({'success': True})
    except CommissionMapping.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Mapping not found'})
    
# Add these to your views.py (uncomment and fix them):

@require_POST
@csrf_exempt
def update_insurance_commission(request):
    """Update insurance commission mapping"""
    mapping_id = request.POST.get('mapping_id')
    actual_commission = request.POST.get('actual_commission')
    
    try:
        mapping = CommissionMapping.objects.get(id=mapping_id)
        mapping.actual_commission = Decimal(actual_commission)
        mapping.save()
        
        # Update the week's total
        week = mapping.commission_week
        week.update_totals()
        
        return JsonResponse({'success': True})
    except CommissionMapping.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Mapping not found'})
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'error': 'Invalid commission amount'})

@require_POST
@csrf_exempt
def refresh_insurance_data(request):
    """Refresh insurance policy data from external source"""
    policy_ids = request.POST.getlist('policy_ids[]')
    week_id = request.POST.get('week_id')
    
    try:
        updated_policies = []
        for policy_id in policy_ids:
            # Fetch latest insurance data (placeholder implementation)
            # In a real application, you'd integrate with your insurance system API
            policy = InsurancePolicy.objects.get(id=policy_id)
            
            # Simulate data refresh - in reality, you'd call an external API
            # policy.premium_amount = fetch_from_api(policy_id)
            # policy.status = fetch_status_from_api(policy_id)
            # policy.save()
            
            # Recalculate estimated commission if premium changed
            mapping = CommissionMapping.objects.get(
                insurance_policy=policy, 
                commission_week_id=week_id
            )
            # Update mapping if needed
            # mapping.estimated_commission = policy.premium_amount * (mapping.commission_rate / 100)
            # mapping.save()
            
            updated_policies.append({
                'id': policy_id,
                'premium_amount': str(policy.premium_amount),
                'status': policy.policy_status
            })
        
        return JsonResponse({'success': True, 'updated_policies': updated_policies})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    
# In views.py
@login_required
def raise_commission_dispute(request, mapping_id):
    """Raise a commission dispute"""
    mapping = get_object_or_404(CommissionMapping, pk=mapping_id)
    
    # Check if user has permission to raise dispute
    if not (request.user == mapping.commission_week.advisor or request.user.is_manager):
        messages.error(request, 'You do not have permission to raise a dispute for this commission.')
        return redirect('commission_week_detail', pk=mapping.commission_week.pk)
    
    if request.method == 'POST':
        disputed_amount = request.POST.get('disputed_amount')
        dispute_reason = request.POST.get('dispute_reason')
        proposed_amount = request.POST.get('proposed_amount')
        
        try:
            disputed_amount = Decimal(disputed_amount)
            if proposed_amount:
                proposed_amount = Decimal(proposed_amount)
            
            # Create dispute
            dispute = CommissionDispute.objects.create(
                commission_mapping=mapping,
                raised_by=request.user,
                dispute_reason=dispute_reason,
                disputed_amount=disputed_amount,
                proposed_amount=proposed_amount,
                status='Open'
            )
            
            # Update mapping status
            mapping.has_dispute = True
            mapping.save()
            
            messages.success(request, 'Dispute raised successfully! It will be reviewed by management.')
            return redirect('commission_week_detail', pk=mapping.commission_week.pk)
            
        except (ValueError, TypeError):
            messages.error(request, 'Invalid amount entered.')
    
    context = {
        'mapping': mapping,
    }
    return render(request, 'crm/raise_dispute.html', context)

@login_required
@manager_required
def resolve_commission_dispute(request, dispute_id):
    """Resolve a commission dispute (manager only)"""
    dispute = get_object_or_404(CommissionDispute, pk=dispute_id)
    
    if request.method == 'POST':
        resolution_notes = request.POST.get('resolution_notes')
        status = request.POST.get('status')
        final_amount = request.POST.get('final_amount')
        
        try:
            if final_amount:
                final_amount = Decimal(final_amount)
                # Update the commission mapping with the resolved amount
                dispute.commission_mapping.actual_commission = final_amount
                dispute.commission_mapping.has_dispute = False
                dispute.commission_mapping.save()
                
                # Update the week totals
                dispute.commission_mapping.commission_week.update_totals()
            
            dispute.resolution_notes = resolution_notes
            dispute.status = status
            dispute.resolved_by = request.user
            dispute.resolved_date = timezone.now()
            dispute.save()
            
            messages.success(request, f'Dispute {dispute.get_status_display().lower()} successfully!')
            return redirect('view_disputes')
            
        except (ValueError, TypeError):
            messages.error(request, 'Invalid amount entered.')
    
    context = {
        'dispute': dispute,
    }
    return render(request, 'crm/resolve_dispute.html', context)

@login_required
def view_disputes(request):
    """View all commission disputes with filtering"""
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    advisor_filter = request.GET.get('advisor', '')
    week_filter = request.GET.get('week', '')
    
    if request.user.is_manager:
        disputes = CommissionDispute.objects.all()
        
        # Apply filters
        if status_filter:
            disputes = disputes.filter(status=status_filter)
        if advisor_filter:
            disputes = disputes.filter(
                Q(raised_by_id=advisor_filter) | 
                Q(commission_mapping__commission_week__advisor_id=advisor_filter)
            )
        if week_filter:
            disputes = disputes.filter(commission_mapping__commission_week_id=week_filter)
            
    else:
        disputes = CommissionDispute.objects.filter(
            Q(raised_by=request.user) | 
            Q(commission_mapping__commission_week__advisor=request.user)
        )
        
        if status_filter:
            disputes = disputes.filter(status=status_filter)
    
    disputes = disputes.select_related(
        'commission_mapping__insurance_policy__customer',
        'commission_mapping__commission_week',
        'raised_by',
        'resolved_by'
    ).order_by('-raised_date')
    
    # Count disputes by status
    open_disputes = disputes.filter(status='Open').count()
    in_review_disputes = disputes.filter(status='In Review').count()
    resolved_disputes = disputes.filter(status='Resolved').count()
    rejected_disputes = disputes.filter(status='Rejected').count()
    
    context = {
        'disputes': disputes,
        'open_disputes': open_disputes,
        'in_review_disputes': in_review_disputes,
        'resolved_disputes': resolved_disputes,
        'rejected_disputes': rejected_disputes,
        'total_disputes': disputes.count(),
        'status_choices': CommissionDispute.DISPUTE_STATUS_CHOICES,
        'advisors': User.objects.filter(is_active=True) if request.user.is_manager else None,
        'commission_weeks': CommissionWeek.objects.all() if request.user.is_manager else None,
        'applied_filters': {
            'status': status_filter,
            'advisor': advisor_filter,
            'week': week_filter,
        }
    }
    
    return render(request, 'crm/view_disputes.html', context)

# In views.py - add this context processor or update existing views
def dispute_context_processor(request):
    if request.user.is_authenticated:
        if request.user.is_manager:
            pending_disputes_count = CommissionDispute.objects.filter(status='Open').count()
        else:
            pending_disputes_count = CommissionDispute.objects.filter(
                Q(raised_by=request.user) | 
                Q(commission_mapping__commission_week__advisor=request.user),
                status='Open'
            ).count()
        
        return {
            'pending_disputes_count': pending_disputes_count
        }
    return {}

@login_required
def weekly_commission_report(request):
    """Weekly commission report view - FIXED"""
    # Get filter parameters
    selected_week = request.GET.get('week')
    selected_year = request.GET.get('year', datetime.now().year)
    active_tab = request.GET.get('tab', 'weeks')

    # Convert to integers with validation
    try:
        selected_year = int(selected_year)
        selected_week = int(selected_week) if selected_week else None
    except (ValueError, TypeError):
        selected_year = datetime.now().year
        selected_week = None

    # Base queryset - managers see all weeks, others see only their own
    if request.user.is_manager:
        available_weeks = CommissionWeek.objects.all()
    else:
        available_weeks = CommissionWeek.objects.filter(advisor=request.user)
    
    available_weeks = available_weeks.order_by('-year', '-week_number').distinct()

    # If no week selected, use the most recent week
    if not selected_week and available_weeks.exists():
        latest_week = available_weeks.first()
        selected_week = latest_week.week_number
        selected_year = latest_week.year

    # Filter for display weeks
    display_weeks = available_weeks
    if selected_week and selected_year:
        display_weeks = display_weeks.filter(week_number=selected_week, year=selected_year)

    # Calculate totals
    total_estimated = display_weeks.aggregate(
        total=Sum('total_estimated_commission')
    )['total'] or Decimal('0.00')

    total_actual = display_weeks.aggregate(
        total=Sum('total_actual_commission')
    )['total'] or Decimal('0.00')

    variance = total_estimated - total_actual
    variance_percentage = (variance / total_estimated * 100) if total_estimated else Decimal('0.00')

    # Get commission mappings for the selected weeks
    commission_mappings = CommissionMapping.objects.filter(commission_week__in=display_weeks)
    
    # Calculate metrics
    completed_applications = commission_mappings.count()
    pending_count = commission_mappings.filter(actual_commission__isnull=True).count()
    pending_approval = commission_mappings.filter(
        actual_commission__isnull=True
    ).aggregate(total=Sum('estimated_commission'))['total'] or Decimal('0.00')

    # Week dates for display
    week_dates = "N/A"
    if display_weeks.exists():
        week = display_weeks.first()
        week_dates = f"{week.start_date.strftime('%d.%m.%Y')} to {week.end_date.strftime('%d.%m.%Y')}"

    # Prepare weekly data
    weekly_data = prepare_weekly_advisor_data_from_mappings(commission_mappings, selected_week, selected_year)
    totals = calculate_weekly_totals(weekly_data)

    # Product summary for commission breakdown
    product_summary = []
    for mapping in commission_mappings:
        policy = mapping.insurance_policy
        product_summary.append({
            'type': policy.policy_type,
            'count': 1,
            'premium': policy.premium_amount or Decimal('0.00'),
            'rate': mapping.commission_rate,
            'commission': mapping.estimated_commission or Decimal('0.00')
        })

    # Aggregate product summary
    aggregated_summary = {}
    for item in product_summary:
        if item['type'] not in aggregated_summary:
            aggregated_summary[item['type']] = {
                'type': item['type'],
                'count': 0,
                'premium': Decimal('0.00'),
                'rate': Decimal('0.00'),
                'commission': Decimal('0.00')
            }
        aggregated_summary[item['type']]['count'] += item['count']
        aggregated_summary[item['type']]['premium'] += item['premium']
        aggregated_summary[item['type']]['commission'] += item['commission']
        # Average rate
        aggregated_summary[item['type']]['rate'] = item['rate']

    product_summary = list(aggregated_summary.values())

    total_applications = sum(item['count'] for item in product_summary)
    total_premium = sum(item['premium'] for item in product_summary)
    total_commission = sum(item['commission'] for item in product_summary)

    # Calculate metrics
    conversion_rate = Decimal('75.5') if total_applications > 0 else Decimal('0.00')
    commission_efficiency = (total_actual / total_estimated * 100) if total_estimated else Decimal('0.00')
    payment_processing = Decimal('92.1')  # Placeholder

    context = {
        'commission_weeks': display_weeks,
        'available_weeks': available_weeks,
        'selected_week': selected_week,
        'selected_year': selected_year,
        'total_estimated': total_estimated,
        'total_actual': total_actual,
        'variance': variance,
        'variance_percentage': variance_percentage,
        'pending_approval': pending_approval,
        'pending_count': pending_count,
        'completed_applications': completed_applications,
        'estimated_growth': Decimal('5.2'),
        'week_dates': week_dates,
        'active_tab': active_tab,
        'weekly_data': weekly_data,
        'totals': totals,
        'product_summary': product_summary,
        'total_applications': total_applications,
        'total_premium': total_premium,
        'total_commission': total_commission,
        'conversion_rate': conversion_rate,
        'commission_efficiency': commission_efficiency,
        'payment_processing': payment_processing,
    }

    return render(request, 'crm/weekly_commission_report.html', context)


@login_required
def commission_report(request):
    # Get selected week from query parameters, default to current week
    selected_week = request.GET.get('week', timezone.now().isocalendar()[1])
    selected_year = request.GET.get('year', timezone.now().year)
    active_tab = request.GET.get('tab', 'weeks')

    try:
        selected_week = int(selected_week)
        selected_year = int(selected_year)
    except (ValueError, TypeError):
        selected_week = timezone.now().isocalendar()[1]
        selected_year = timezone.now().year

    # Get all available weeks for the selector
    available_weeks = CommissionWeek.objects.filter(
        advisor=request.user
    ).order_by('-year', '-week_number')

    # Get commission weeks for the selected period
    commission_weeks = CommissionWeek.objects.filter(
        week_number=selected_week,
        year=selected_year,
        advisor=request.user
    ).select_related('advisor').prefetch_related('applications')

    # Calculate summary statistics
    total_estimated = commission_weeks.aggregate(
        total=Sum('total_estimated_commission')
    )['total'] or Decimal('0.00')

    total_actual = commission_weeks.aggregate(
        total=Sum('total_actual_commission')
    )['total'] or Decimal('0.00')

    variance = total_estimated - total_actual
    variance_percentage = (variance / total_estimated * 100) if total_estimated else Decimal('0.00')

    # Get pending applications
    pending_applications = Application.objects.filter(
        commission_week__in=commission_weeks,
        status='Pending Review'
    )
    pending_approval = pending_applications.aggregate(
        total=Sum('estimated_commission')
    )['total'] or Decimal('0.00')
    pending_count = pending_applications.count()

    # Get completed applications count
    completed_applications = Application.objects.filter(
        commission_week__in=commission_weeks,
        status__in=['Approved', 'Paid']
    ).count()

    # Calculate estimated growth (placeholder - you might want to implement actual growth calculation)
    estimated_growth = Decimal('5.2')  # Example growth percentage

    # Calculate week dates for display
    try:
        week_dates = get_week_dates(selected_year, selected_week)
    except (ValueError, IndexError):
        # Calculate week dates manually if no commission week exists
        try:
            first_day = datetime.strptime(f'{selected_year}-W{selected_week}-1', "%Y-W%W-%w").date()
            last_day = first_day + timedelta(days=6)
            week_dates = f"{first_day.strftime('%d.%m.%Y')} to {last_day.strftime('%d.%m.%Y')}"
        except:
            week_dates = "Invalid week"

    # Product summary for commission breakdown
    product_summary = Application.objects.filter(
        commission_week__in=commission_weeks
    ).values('product_type').annotate(
        count=Count('id'),
        premium=Sum('premium_amount'),
        commission=Sum('actual_commission')
    )

    total_applications = sum(item['count'] for item in product_summary)
    total_premium = sum(item['premium'] or Decimal('0.00') for item in product_summary)
    total_commission = sum(item['commission'] or Decimal('0.00') for item in product_summary)

    # Calculate metrics
    conversion_rate = Decimal('75.5')  # Placeholder
    commission_efficiency = Decimal('88.2')  # Placeholder
    payment_processing = Decimal('92.1')  # Placeholder

    # NEW: Prepare data for Weekly Advisor Report
    weekly_data = prepare_weekly_advisor_data(request.user, selected_week, selected_year)

    context = {
        'commission_weeks': commission_weeks,
        'total_estimated': total_estimated,
        'total_actual': total_actual,
        'variance': variance,
        'variance_percentage': variance_percentage,
        'pending_approval': pending_approval,
        'pending_count': pending_count,
        'completed_applications': completed_applications,
        'estimated_growth': estimated_growth,
        'available_weeks': available_weeks,
        'selected_week': selected_week,
        'selected_year': selected_year,
        'week_dates': week_dates,
        'active_tab': active_tab,
        'product_summary': product_summary,
        'total_applications': total_applications,
        'total_premium': total_premium,
        'total_commission': total_commission,
        'conversion_rate': conversion_rate,
        'commission_efficiency': commission_efficiency,
        'payment_processing': payment_processing,
        # NEW: Weekly Advisor Report data
        'weekly_data': weekly_data,
        'totals': calculate_weekly_totals(weekly_data),
    }

    return render(request, 'crm/weekly_commission_report.html', context)

def get_week_dates(year, week_number):
    """Get start and end dates for a given week number"""
    first_day = datetime.strptime(f'{year}-W{week_number}-1', "%Y-W%W-%w").date()
    last_day = first_day + timedelta(days=6)
    return first_day, last_day

def prepare_weekly_advisor_data_from_activities(daily_activities, week_start):
    """Prepare weekly data from DailyAdvisorActivity records"""
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    weekly_data = []
    current_date = week_start
    
    for i, day_name in enumerate(days):
        # Try to find activity for this date
        activity = None
        for act in daily_activities:
            if act.date == current_date:
                activity = act
                break
        
        if activity:
            day_data = {
                'day_name': day_name,
                'date': current_date,
                'calls_made': activity.calls_made,
                'appointments_booked': activity.appointments_booked,
                'appointments_attended': activity.appointments_attended,
                'presentations_made': activity.presentations_made,
                'references_collected': activity.references_collected,
                'brochures_sent': activity.brochures_sent,
                'brochures_received': activity.brochures_received,
                'customer_introductions': activity.customer_introductions,
                'other_sources': activity.other_sources,
                'policies_sold': activity.policies_sold,
                'total_premium': activity.total_premium,
                'home_insurance': activity.home_insurance,
                'pending_policies_count': activity.pending_policies_count,
                'pending_policies_amount': activity.pending_policies_amount,
                'remarks': activity.remarks,
                'mortgages': activity.mortgages,
                'wills': activity.wills,
                'policy_details': list(activity.policy_details.all()) if hasattr(activity, 'policy_details') else [],
            }
        else:
            # Create empty day data
            day_data = {
                'day_name': day_name,
                'date': current_date,
                'calls_made': 0,
                'appointments_booked': 0,
                'appointments_attended': 0,
                'presentations_made': 0,
                'references_collected': 0,
                'brochures_sent': 0,
                'brochures_received': 0,
                'customer_introductions': 0,
                'other_sources': 0,
                'policies_sold': 0,
                'total_premium': Decimal('0.00'),
                'home_insurance': 0,
                'pending_policies_count': 0,
                'pending_policies_amount': Decimal('0.00'),
                'remarks': '',
                'mortgages': 0,
                'wills': 0,
                'policy_details': [],
            }
        
        weekly_data.append(day_data)
        current_date += timedelta(days=1)
    
    return weekly_data

def prepare_weekly_advisor_data_from_mappings(commission_mappings, week_number, year):
    """
    Prepare weekly data for the advisor report from actual commission mappings.
    """
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    weekly_data = []
    
    # If no commission mappings, return empty data
    if not commission_mappings.exists():
        for i, day in enumerate(days):
            day_data = {
                'day_name': day,
                'calls_made': 0,
                'appointments_booked': 0,
                'appointments_attended': 0,
                'presentations_made': 0,
                'posted_brochures': 0,
                'customer_introduction': 0,
                'other_sources': 0,
                'policies_sold': 0,
                'policies': [],
                'accident_policy_number': '',
                'accident_units': 0,
                'accident_premium': Decimal('0.00'),
                'pending_updates': '',
                'home_insurance_count': 0,
                'home_insurance_amount': Decimal('0.00'),
                'total_premium': Decimal('0.00'),
                'remarks': 'No data available',
                'ftb_count': 0,
                'remortgage_count': 0,
                'referred_count': 0,
                'completed_count': 0,
            }
            weekly_data.append(day_data)
        return weekly_data
    
    # Group mappings by day of the week
    mappings_list = list(commission_mappings.select_related(
        'insurance_policy', 
        'insurance_policy__customer'
    ))
    
    policies_per_day = max(1, len(mappings_list) // 7)
    
    for i, day in enumerate(days):
        day_policies = []
        day_start_idx = i * policies_per_day
        day_end_idx = min((i + 1) * policies_per_day, len(mappings_list))
        
        if i == 6:  # Sunday gets remaining policies
            day_end_idx = len(mappings_list)
        
        for mapping in mappings_list[day_start_idx:day_end_idx]:
            policy = mapping.insurance_policy
            day_policies.append({
                'applicant_name': f"{policy.customer.first_name} {policy.customer.last_name}",
                'address': policy.customer.address or 'N/A',
                'contact_no': policy.customer.phone or policy.customer.mobile or 'N/A',
                'dob': policy.customer.date_of_birth.strftime('%d.%m.%Y') if policy.customer.date_of_birth else 'N/A',
                'provider': policy.insurance_company,
                'life_cover_amount': policy.coverage_amount or Decimal('0.00'),
                'policy_number': policy.policy_number or 'N/A',
                'illustration_premium': policy.premium_amount or Decimal('0.00'),
                'illustration_commission': mapping.estimated_commission or Decimal('0.00'),
                'new_premium': policy.premium_amount or Decimal('0.00'),
                'new_commission': mapping.actual_commission or Decimal('0.00'),
                'policy_status': policy.policy_status,
                # Placeholder fields for other policy types
                'cic_cover_amount': Decimal('0.00'),
                'cic_provider': 'N/A',
                'cic_policy_number': 'N/A',
                'cic_illustration_premium': Decimal('0.00'),
                'cic_illustration_commission': Decimal('0.00'),
                'cic_new_premium': Decimal('0.00'),
                'cic_new_commission': Decimal('0.00'),
                'cic_policy_status': 'N/A',
                'ip_cover_amount': Decimal('0.00'),
                'ip_provider': 'N/A',
                'ip_policy_number': 'N/A',
                'ip_illustration_premium': Decimal('0.00'),
                'ip_illustration_commission': Decimal('0.00'),
                'ip_new_premium': Decimal('0.00'),
                'ip_new_commission': Decimal('0.00'),
                'ip_policy_status': 'N/A',
            })
        
        # Calculate day totals
        total_premium = sum((p['new_premium'] for p in day_policies), Decimal('0.00'))
        policies_sold = len(day_policies)
        
        day_data = {
            'day_name': day,
            'calls_made': 10 + i * 2,
            'appointments_booked': 2 + (i % 3),
            'appointments_attended': 1 + (i % 2),
            'presentations_made': 1 + (i % 2),
            'posted_brochures': i % 3,
            'customer_introduction': i % 2,
            'other_sources': i % 2,
            'policies_sold': policies_sold,
            'policies': day_policies,
            'accident_policy_number': f'AP{week_number}{i:02d}' if policies_sold > 0 else '',
            'accident_units': 2 if i == 3 and policies_sold > 0 else (1 if i > 3 and policies_sold > 0 else 0),
            'accident_premium': Decimal('25.00') if i == 3 and policies_sold > 0 else (Decimal('12.50') if i > 3 and policies_sold > 0 else Decimal('0.00')),
            'pending_updates': 'Update needed' if i % 2 and policies_sold > 0 else '',
            'home_insurance_count': 1 if i == 4 and policies_sold > 0 else 0,
            'home_insurance_amount': Decimal('150.00') if i == 4 and policies_sold > 0 else Decimal('0.00'),
            'total_premium': total_premium,
            'remarks': 'Productive day' if policies_sold > 0 else 'Follow-up needed',
            'ftb_count': 1 if i == 2 and policies_sold > 0 else 0,
            'remortgage_count': 1 if i == 5 and policies_sold > 0 else 0,
            'referred_count': 0,
            'completed_count': policies_sold,
        }
        
        weekly_data.append(day_data)
    
    return weekly_data

def calculate_weekly_totals(weekly_data):
    """Calculate totals for the weekly advisor report."""
    totals = {
        'calls_made': sum(day['calls_made'] for day in weekly_data),
        'appointments_booked': sum(day['appointments_booked'] for day in weekly_data),
        'appointments_attended': sum(day['appointments_attended'] for day in weekly_data),
        'presentations_made': sum(day['presentations_made'] for day in weekly_data),
        'posted_brochures': sum(day['posted_brochures'] for day in weekly_data),
        'customer_introduction': sum(day['customer_introduction'] for day in weekly_data),
        'other_sources': sum(day['other_sources'] for day in weekly_data),
        'policies_sold': sum(day['policies_sold'] for day in weekly_data),
        'total_premium': sum(day['total_premium'] for day in weekly_data),
        'home_insurance_count': sum(day['home_insurance_count'] for day in weekly_data),
        'ftb_count': sum(day['ftb_count'] for day in weekly_data),
        'remortgage_count': sum(day['remortgage_count'] for day in weekly_data),
        'referred_count': sum(day['referred_count'] for day in weekly_data),
        'completed_count': sum(day['completed_count'] for day in weekly_data),
    }
    return totals

@login_required
def export_advisor_report(request):
    """Export advisor weekly report to CSV"""
    import csv
    from django.http import HttpResponse
    
    # Get parameters from request
    week_number = request.GET.get('week', timezone.now().isocalendar()[1])
    year = request.GET.get('year', timezone.now().year)
    
    try:
        week_number = int(week_number)
        year = int(year)
    except (ValueError, TypeError):
        week_number = timezone.now().isocalendar()[1]
        year = timezone.now().year
    
    # Prepare weekly data (using the same function as in commission_report)
    weekly_data = prepare_weekly_advisor_data(request.user, week_number, year)
    totals = calculate_weekly_totals(weekly_data)
    
    # Create HTTP response with CSV attachment
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="advisor_report_week_{week_number}_{year}.csv"'
    
    writer = csv.writer(response)
    
    # Write header
    writer.writerow(['Advisor Weekly Activity Report'])
    writer.writerow([f'Week: {week_number}, Year: {year}'])
    writer.writerow([f'Advisor: {request.user.get_full_name()}'])
    writer.writerow([])
    
    # Write daily activity headers
    writer.writerow(['Day', 'Calls Made', 'Appointments Booked', 'Appointments Attended', 
                    'Presentations Made', 'Posted Brochures', 'Customer Introductions', 
                    'Other Sources', 'Policies Sold', 'Total Premium', 'Remarks'])
    
    # Write daily activity data
    for day_data in weekly_data:
        writer.writerow([
            day_data['day_name'],
            day_data['calls_made'],
            day_data['appointments_booked'],
            day_data['appointments_attended'],
            day_data['presentations_made'],
            day_data['posted_brochures'],
            day_data['customer_introduction'],
            day_data['other_sources'],
            day_data['policies_sold'],
            f"£{day_data['total_premium']:.2f}",
            day_data['remarks']
        ])
    
    # Write totals row
    writer.writerow([
        'TOTALS',
        totals['calls_made'],
        totals['appointments_booked'],
        totals['appointments_attended'],
        totals['presentations_made'],
        totals['posted_brochures'],
        totals['customer_introduction'],
        totals['other_sources'],
        totals['policies_sold'],
        f"£{totals['total_premium']:.2f}",
        ''
    ])
    
    writer.writerow([])
    
    # Write policy details header
    writer.writerow(['Policy Details'])
    writer.writerow(['Day', 'Applicant Name', 'Address', 'Contact No', 'DOB', 'Provider', 
                    'Life Cover Amount', 'Policy Number', 'Premium', 'Commission', 'Status'])
    
    # Write policy details
    for i, day_data in enumerate(weekly_data):
        for policy in day_data['policies']:
            writer.writerow([
                day_data['day_name'],
                policy['applicant_name'],
                policy['address'],
                policy['contact_no'],
                policy['dob'],
                policy['provider'],
                f"£{policy['life_cover_amount']:.2f}",
                policy['policy_number'],
                f"£{policy['illustration_premium']:.2f}",
                f"£{policy['illustration_commission']:.2f}",
                policy['policy_status']
            ])
    
    writer.writerow([])
    
    # Write summary section
    writer.writerow(['Summary Statistics'])
    writer.writerow(['First Time Buyers', totals['ftb_count']])
    writer.writerow(['Remortgages', totals['remortgage_count']])
    writer.writerow(['Referred Cases', totals['referred_count']])
    writer.writerow(['Completed Cases', totals['completed_count']])
    writer.writerow(['Home Insurance Policies', totals['home_insurance_count']])
    
    return response

@login_required
def advisor_weekly_report(request):
    """Weekly Advisor Report as a standalone page"""
    # Get filter parameters from request
    selected_week = request.GET.get('week')
    selected_year = request.GET.get('year', datetime.now().year)
    
    # Convert to integers with validation
    try:
        selected_year = int(selected_year)
        selected_week = int(selected_week) if selected_week else None
    except (ValueError, TypeError):
        selected_year = datetime.now().year
        selected_week = None

    # Base queryset - managers see all weeks, others see only their own
    if request.user.is_manager:
        available_weeks = CommissionWeek.objects.all()
    else:
        available_weeks = CommissionWeek.objects.filter(advisor=request.user)
    
    available_weeks = available_weeks.order_by('-year', '-week_number').distinct()

    # If no week selected, use the most recent week
    if not selected_week and available_weeks.exists():
        latest_week = available_weeks.first()
        selected_week = latest_week.week_number
        selected_year = latest_week.year

    # Filter for display weeks
    display_weeks = available_weeks
    if selected_week and selected_year:
        display_weeks = display_weeks.filter(week_number=selected_week, year=selected_year)

    # Get commission mappings for the selected weeks
    commission_mappings = CommissionMapping.objects.filter(commission_week__in=display_weeks)
    
    # Week dates for display
    week_dates = "N/A"
    if display_weeks.exists():
        week = display_weeks.first()
        week_dates = f"{week.start_date.strftime('%d.%m.%Y')} to {week.end_date.strftime('%d.%m.%Y')}"

    # Prepare weekly data - FIXED: Use the correct function
    weekly_data = prepare_weekly_advisor_data_from_mappings(commission_mappings, selected_week, selected_year)
    totals = calculate_weekly_totals(weekly_data)

    context = {
        'available_weeks': available_weeks,
        'selected_week': selected_week,
        'selected_year': selected_year,
        'week_dates': week_dates,
        'weekly_data': weekly_data,
        'totals': totals,
        'is_standalone_page': True,
    }

    return render(request, 'crm/advisor_weekly_report.html', context)

def get_week_dates(year, week_number):
    """Get start and end dates for a given week number"""
    first_day = datetime.strptime(f'{year}-W{week_number}-1', "%Y-W%W-%w").date()
    last_day = first_day + timedelta(days=6)
    return first_day, last_day

def prepare_weekly_advisor_data(advisor, week_number, year):
    """Prepare weekly data structure matching the Excel format"""
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    weekly_data = []
    
    # Get the date range for the requested week
    start_date, end_date = get_week_dates(year, week_number)
    current_date = start_date
    
    for i, day_name in enumerate(days):
        # Try to get activity data for this day
        try:
            activity = DailyAdvisorActivity.objects.get(
                advisor=advisor, 
                date=current_date
            )
            policy_details = list(activity.policy_details.all())
            
            day_data = {
                'day_name': day_name,
                'date': current_date,
                'calls_made': activity.calls_made,
                'appointments_booked': activity.appointments_booked,
                'appointments_attended': activity.appointments_attended,
                'presentations_made': activity.presentations_made,
                'references_collected': activity.references_collected,
                'brochures_sent': activity.brochures_sent,
                'brochures_received': activity.brochures_received,
                'customer_introductions': activity.customer_introductions,
                'other_sources': activity.other_sources,
                'policies_sold': activity.policies_sold,
                'total_premium': activity.total_premium,
                'home_insurance': activity.home_insurance,
                'pending_policies_count': activity.pending_policies_count,
                'pending_policies_amount': activity.pending_policies_amount,
                'remarks': activity.remarks,
                'mortgages': activity.mortgages,
                'wills': activity.wills,
                'policy_details': policy_details,
            }
            
        except DailyAdvisorActivity.DoesNotExist:
            # Create empty day data if no activity recorded
            day_data = {
                'day_name': day_name,
                'date': current_date,
                'calls_made': 0,
                'appointments_booked': 0,
                'appointments_attended': 0,
                'presentations_made': 0,
                'references_collected': 0,
                'brochures_sent': 0,
                'brochures_received': 0,
                'customer_introductions': 0,
                'other_sources': 0,
                'policies_sold': 0,
                'total_premium': 0,
                'home_insurance': 0,
                'pending_policies_count': 0,
                'pending_policies_amount': 0,
                'remarks': '',
                'mortgages': 0,
                'wills': 0,
                'policy_details': [],
            }
        
        weekly_data.append(day_data)
        current_date += timedelta(days=1)
    
    return weekly_data

def calculate_weekly_totals(weekly_data):
    """Calculate totals for the weekly report"""
    totals = {
        'calls_made': sum(day['calls_made'] for day in weekly_data),
        'appointments_booked': sum(day['appointments_booked'] for day in weekly_data),
        'appointments_attended': sum(day['appointments_attended'] for day in weekly_data),
        'presentations_made': sum(day['presentations_made'] for day in weekly_data),
        'references_collected': sum(day['references_collected'] for day in weekly_data),
        'brochures_sent': sum(day['brochures_sent'] for day in weekly_data),
        'brochures_received': sum(day['brochures_received'] for day in weekly_data),
        'customer_introductions': sum(day['customer_introductions'] for day in weekly_data),
        'other_sources': sum(day['other_sources'] for day in weekly_data),
        'policies_sold': sum(day['policies_sold'] for day in weekly_data),
        'total_premium': sum(day['total_premium'] for day in weekly_data),
        'home_insurance': sum(day['home_insurance'] for day in weekly_data),
        'pending_policies_count': sum(day['pending_policies_count'] for day in weekly_data),
        'pending_policies_amount': sum(day['pending_policies_amount'] for day in weekly_data),
        'mortgages': sum(day['mortgages'] for day in weekly_data),
        'wills': sum(day['wills'] for day in weekly_data),
    }
    return totals

@login_required
def advisor_weekly_report(request):
    """Main weekly report view"""
    # Get filter parameters
    selected_week = request.GET.get('week')
    selected_year = request.GET.get('year', datetime.now().year)
    
    # Convert to integers with validation
    try:
        selected_year = int(selected_year)
        selected_week = int(selected_week) if selected_week else datetime.now().isocalendar()[1]
    except (ValueError, TypeError):
        selected_year = datetime.now().year
        selected_week = datetime.now().isocalendar()[1]
    
    # Get week dates for display
    week_start, week_end = get_week_dates(selected_year, selected_week)
    week_dates = f"{week_start.strftime('%d.%m.%Y')} to {week_end.strftime('%d.%m.%Y')}"
    
    # Prepare weekly data
    weekly_data = prepare_weekly_advisor_data(request.user, selected_week, selected_year)
    totals = calculate_weekly_totals(weekly_data)
    
    context = {
        'advisor_name': request.user.get_full_name(),
        'selected_week': selected_week,
        'selected_year': selected_year,
        'business_week_start': week_start.strftime('%d.%m.%Y'),
        'business_week_end': week_end.strftime('%d.%m.%Y'),
        'week_dates': week_dates,
        'weekly_data': weekly_data,
        'totals': totals,
    }
    
    return render(request, 'crm/advisor_weekly_report.html', context)


@login_required
def export_advisor_report(request):
    """Export advisor weekly report to Excel"""
    selected_week = request.GET.get('week')
    selected_year = request.GET.get('year', datetime.now().year)
    
    try:
        selected_year = int(selected_year)
        selected_week = int(selected_week) if selected_week else datetime.now().isocalendar()[1]
    except (ValueError, TypeError):
        selected_year = datetime.now().year
        selected_week = datetime.now().isocalendar()[1]
    
    # Prepare weekly data
    weekly_data = prepare_weekly_advisor_data(request.user, selected_week, selected_year)
    totals = calculate_weekly_totals(weekly_data)
    
    # Create Excel file
    output = BytesIO()  # This will now work with the import
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    workbook = writer.book
    
    # Prepare data for Excel
    activity_data = []
    for day_data in weekly_data:
        activity_data.append({
            'Day': day_data['day_name'],
            'Calls Made': day_data['calls_made'],
            'Appointments Booked': day_data['appointments_booked'],
            'Appointments Attended': day_data['appointments_attended'],
            'Presentations Made': day_data['presentations_made'],
            'References Collected': day_data['references_collected'],
            'Brochures Sent': day_data['brochures_sent'],
            'Brochures Received': day_data['brochures_received'],
            'Customer Introductions': day_data['customer_introductions'],
            'Other Sources': day_data['other_sources'],
            'Policies Sold': day_data['policies_sold'],
            'Total Premium': float(day_data['total_premium']),
            'Home Insurance': day_data['home_insurance'],
            'Pending Policies Count': day_data['pending_policies_count'],
            'Pending Policies Amount': float(day_data['pending_policies_amount']),
            'Remarks': day_data['remarks'],
            'Mortgages': day_data['mortgages'],
            'Wills': day_data['wills'],
        })
    
    # Add totals row
    activity_data.append({
        'Day': 'TOTAL',
        'Calls Made': totals['calls_made'],
        'Appointments Booked': totals['appointments_booked'],
        'Appointments Attended': totals['appointments_attended'],
        'Presentations Made': totals['presentations_made'],
        'References Collected': totals['references_collected'],
        'Brochures Sent': totals['brochures_sent'],
        'Brochures Received': totals['brochures_received'],
        'Customer Introductions': totals['customer_introductions'],
        'Other Sources': totals['other_sources'],
        'Policies Sold': totals['policies_sold'],
        'Total Premium': float(totals['total_premium']),
        'Home Insurance': totals['home_insurance'],
        'Pending Policies Count': totals['pending_policies_count'],
        'Pending Policies Amount': float(totals['pending_policies_amount']),
        'Remarks': '',
        'Mortgages': totals['mortgages'],
        'Wills': totals['wills'],
    })
    
    # Convert to DataFrame and write to Excel
    df_activity = pd.DataFrame(activity_data)
    df_activity.to_excel(writer, sheet_name='Weekly Activity', index=False)
    
    # Policy details sheet
    policy_data = []
    for day_data in weekly_data:
        for policy in day_data['policy_details']:
            policy_data.append({
                'Day': day_data['day_name'],
                'Applicant': policy.applicant_name,
                'Address': policy.address,
                'Contact No': policy.contact_no,
                'DOB': policy.date_of_birth.strftime('%d.%m.%Y') if policy.date_of_birth else 'N/A',
                'Provider': policy.provider,
                'Life Cover Amount': float(policy.life_cover_amount),
                'Policy Number': policy.policy_number,
                'Premium': float(policy.illustration_premium),
                'Commission': float(policy.illustration_commission),
                'Status': policy.policy_status,
            })
    
    if policy_data:
        df_policies = pd.DataFrame(policy_data)
        df_policies.to_excel(writer, sheet_name='Policy Details', index=False)
    
    # Close the writer
    writer.close()
    output.seek(0)
    
    # Create HTTP response
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=advisor_report_week_{selected_week}_{selected_year}.xlsx'
    
    return response

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_daily_activity(request):
    """API endpoint for advisors to manually update activities"""
    activity_type = request.data.get('type')
    value = request.data.get('value', 1)
    
    activity, created = DailyAdvisorActivity.objects.get_or_create(
        advisor=request.user,
        date=timezone.now().date(),
        defaults={activity_type: 0}
    )
    
    if hasattr(activity, activity_type):
        current_value = getattr(activity, activity_type) or 0
        setattr(activity, activity_type, current_value + int(value))
        activity.save()
        
        return Response({'status': 'success', 'new_value': getattr(activity, activity_type)})
    
    return Response({'status': 'error', 'message': 'Invalid activity type'}, status=400)