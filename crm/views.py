# views.py
from django.contrib.auth import login, authenticate, logout
from django.views.decorators.http import require_http_methods
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib import messages
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.contrib.auth import get_user_model  
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView,TemplateView
from django.views.decorators.http import require_POST
from django.db import transaction
from decimal import Decimal
from django.views.decorators.csrf import csrf_protect
from .forms import DocumentForm, CommunicationForm, PaymentForm, CommissionWeekForm, CommissionApplicationMappingForm
from django.db import models
from django.db.models import Q, Count, Sum, Avg 
from django.db.models.functions import TruncMonth, TruncYear
from collections import defaultdict
import calendar
from datetime import datetime, timedelta, date
import datetime


from .models import (
    Customer, Mortgage, InsurancePolicy, Application,
    Document, Communication, Commission, Payment, CommissionWeek, CommissionApplicationMapping,CommissionWeek, CommissionMapping, Application
)
from .forms import (
    CustomerForm, MortgageForm, InsurancePolicyForm,
    ApplicationForm, CommunicationForm, AdvisorForm, CommissionMappingForm
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

    def get_queryset(self):
        # Remove advisor filter to allow editing all mortgages
        # return Mortgage.objects.filter(advisor=self.request.user)
        return Mortgage.objects.all()

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
        # Remove advisor filter to show all insurance policies
        # return InsurancePolicy.objects.filter(advisor=self.request.user).order_by('-created_at')
        return InsurancePolicy.objects.all().order_by('-created_at')
        
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
        # Remove advisor filter to allow access to all insurance policies
        # return InsurancePolicy.objects.filter(advisor=self.request.user)
        return InsurancePolicy.objects.all()

class InsuranceUpdateView(LoginRequiredMixin, UpdateView):
    model = InsurancePolicy
    form_class = InsurancePolicyForm
    template_name = 'crm/insurance_form.html'
    success_url = reverse_lazy('insurance_list')

    def get_queryset(self):
        # Remove advisor filter to allow editing all insurance policies
        # return InsurancePolicy.objects.filter(advisor=self.request.user)
        return InsurancePolicy.objects.all()

    def form_valid(self, form):
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

# views.py - Add advanced search function
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

        context['documents'] = Document.objects.filter(application=application)
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

    def form_valid(self, form):
        messages.success(self.request, 'Application updated successfully!')
        return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['customer'].queryset = Customer.objects.all()
        form.fields['mortgage'].queryset = Mortgage.objects.all()
        form.fields['insurance'].queryset = InsurancePolicy.objects.all()
        return form

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
                                    mortgage=mortgage,
                                    advisor=request.user,
                                    application_number=application_number
                                )
                                applications_created += 1
                                print(f"DEBUG: Created mortgage application: {application}")
                                
                            except Mortgage.DoesNotExist:
                                messages.warning(request, f'Mortgage with ID {mortgage_id} not found')
                        
                        # Create applications for each selected insurance type
                        for insurance_type in insurance_types:
                            # Generate application number for insurance
                            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
                            prefix = insurance_abbreviations.get(insurance_type, 'INS')
                            application_number = f"APP_INS_{prefix}_{request.user.id}_{timestamp}_{applications_created}"
                            
                            # Generate insurance ID
                            insurance_timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
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
                                insurance=insurance_policy,
                                insurance_type=insurance_type,
                                advisor=request.user,
                                application_number=application_number
                            )
                            applications_created += 1
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
def add_document(request, pk):
    """Standalone view to add a document to an application"""
    application = get_object_or_404(Application, pk=pk)
    
    if request.method == 'POST':
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
    
    return redirect('application_detail', pk=application.pk)    

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
    """Commission week detail view"""
    week = get_object_or_404(CommissionWeek, pk=pk)
    mappings = CommissionApplicationMapping.objects.filter(commission_week=week)

    context = {
        'week': week,
        'mappings': mappings,
    }
    return render(request, 'crm/commission_week_detail.html', context)

@login_required
def commission_week_create(request):
    """Create a new commission week with proper week number validation"""
    if request.method == 'POST':
        form = CommissionWeekForm(request.POST)
        if form.is_valid():
            # Validate week number is current or future week
            today = date.today()
            year = today.year
            week_number = today.isocalendar()[1]
            
            submitted_week = form.cleaned_data['week_number']
            submitted_year = form.cleaned_data['year']
            
            # Validate week number is valid (1-52/53)
            if submitted_week < 1 or submitted_week > 53:
                form.add_error('week_number', 'Week number must be between 1 and 53')
            # Validate year is current or future
            elif submitted_year < year:
                form.add_error('year', 'Cannot create commission weeks for past years')
            # Validate week is current or future for current year
            elif submitted_year == year and submitted_week < week_number:
                form.add_error('week_number', 'Cannot create commission weeks for past weeks')
                
            if not form.errors:
                week = form.save()
                messages.success(request, 'Commission week created successfully!')
                return redirect('commission_week_detail', pk=week.pk)
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
def assign_application_to_week(request, application_id):
    """Assign application to a commission week with validation"""
    application = get_object_or_404(Application, pk=application_id)
    
    # Validate application is eligible (insurance with Active/Underwriter status)
    if application.application_type == 'Insurance' and application.insurance:
        if application.insurance.policy_status not in ['Active', 'Underwriter']:
            messages.error(request, 'Only insurance applications with status "Active" or "Underwriter" can be assigned to commission weeks.')
            return redirect('application_detail', pk=application_id)
    else:
        messages.error(request, 'Only insurance applications can be assigned to commission weeks.')
        return redirect('application_detail', pk=application_id)

    # Check if application is already mapped
    existing_mapping = CommissionApplicationMapping.objects.filter(application=application).first()
    if existing_mapping:
        messages.warning(request, 'This application is already assigned to a commission week.')
        return redirect('application_detail', pk=application_id)

    if request.method == 'POST':
        form = CommissionApplicationMappingForm(request.POST)
        if form.is_valid():
            mapping = form.save(commit=False)
            mapping.application = application

            # Calculate estimated commission for insurance
            if application.insurance:
                mapping.estimated_commission = application.insurance.premium_amount * Decimal('0.2')  # 20% example
                mapping.commission_rate = Decimal('20.0')

            mapping.save()

            # Update commission week totals
            week = mapping.commission_week
            week.total_estimated_commission += mapping.estimated_commission
            week.save()

            messages.success(request, 'Application assigned to commission week successfully!')
            return redirect('commission_week_detail', pk=week.pk)
    else:
        # Only show current and future weeks
        current_date = date.today()
        current_week = current_date.isocalendar()[1]
        current_year = current_date.year
        
        future_weeks = CommissionWeek.objects.filter(
            Q(year__gt=current_year) | 
            Q(year=current_year, week_number__gte=current_week)
        ).filter(advisor=request.user)
        
        form = CommissionApplicationMappingForm()
        form.fields['commission_week'].queryset = future_weeks

    context = {
        'form': form,
        'application': application,
    }
    return render(request, 'crm/assign_to_week.html', context)

@login_required
def update_commission_mapping(request, mapping_id):
    """Update commission mapping (for managers to set actual commission)"""
    mapping = get_object_or_404(CommissionApplicationMapping, pk=mapping_id)

    if not request.user.is_manager:
        messages.error(request, 'Only managers can update commission amounts.')
        return redirect('commission_week_detail', pk=mapping.commission_week.pk)

    if request.method == 'POST':
        form = CommissionApplicationMappingForm(request.POST, instance=mapping)
        if form.is_valid():
            old_actual = mapping.actual_commission or Decimal('0')
            mapping = form.save(commit=False)
            mapping.updated_by = request.user  # Track which manager made the update
            mapping.save()

            # Update commission week totals
            week = mapping.commission_week
            if mapping.actual_commission:
                week.total_actual_commission = (week.total_actual_commission or Decimal('0')) - old_actual + mapping.actual_commission
            week.save()

            messages.success(request, 'Commission mapping updated successfully!')
            return redirect('commission_week_detail', pk=week.pk)
    else:
        form = CommissionApplicationMappingForm(instance=mapping)

    context = {
        'form': form,
        'mapping': mapping,
    }
    return render(request, 'crm/commission_mapping_form.html', context)

@login_required
def submit_week_for_approval(request, week_id):
    """Advisor submits week for manager approval"""
    week = get_object_or_404(CommissionWeek, pk=week_id, advisor=request.user)
    
    if week.status != 'Open':
        messages.error(request, 'Only open weeks can be submitted for approval.')
        return redirect('commission_week_detail', pk=week_id)
    
    # Validate that week has applications
    if not CommissionApplicationMapping.objects.filter(commission_week=week).exists():
        messages.error(request, 'Cannot submit empty week for approval.')
        return redirect('commission_week_detail', pk=week_id)
    
    week.status = 'Pending Review'
    week.save()
    
    messages.success(request, f'Week {week.week_number} submitted for manager approval.')
    return redirect('commission_week_detail', pk=week_id)


@login_required
def weekly_commission_report(request):
    """Weekly commission report view"""
    # Get filter parameters from request
    year = request.GET.get('year', datetime.now().year)
    advisor_id = request.GET.get('advisor')
    status = request.GET.get('status')

    # Convert year to integer
    try:
        year = int(year)
    except (ValueError, TypeError):
        year = datetime.now().year

    # Initialize variables at the beginning
    total_estimated = Decimal('0')
    total_actual = Decimal('0')

    # Base queryset
    weeks = CommissionWeek.objects.filter(year=year)

    # Apply filters
    if advisor_id:
        weeks = weeks.filter(advisor_id=advisor_id)
    if status:
        weeks = weeks.filter(status=status)

    weeks = weeks.order_by('-year', '-week_number')

    # Calculate totals
    for week in weeks:
        total_estimated += week.total_estimated_commission or Decimal('0')
        total_actual += week.total_actual_commission or Decimal('0')

    # Calculate variance
    variance = total_estimated - total_actual

    context = {
        'weeks': weeks,
        'advisors': User.objects.filter(is_active=True),
        'status_choices': CommissionWeek._meta.get_field('status').choices,
        'years': range(datetime.now().year - 2, datetime.now().year + 3),
        'selected_year': year,
        'selected_advisor': advisor_id,
        'selected_status': status,
        'total_estimated': total_estimated,
        'total_actual': total_actual,
        'variance': variance,
    }

    return render(request, 'crm/weekly_commission_report.html', context)

# views.py
from datetime import datetime, timedelta  
from django.utils import timezone
@login_required
def auto_assign_applications(request):
    """Automatically assign eligible applications to current commission week"""
    if not request.user.is_manager:
        messages.error(request, 'Only managers can auto-assign applications.')
        return redirect('dashboard')

    # Get current week number using ISO standard
    current_date = timezone.now().date()
    week_number = current_date.isocalendar()[1]
    year = current_date.year

    assigned_count = 0

    for advisor in User.objects.filter(is_active=True):
        # Get current week or create it with proper dates
        week_start = current_date - timedelta(days=current_date.weekday())
        week_end = week_start + timedelta(days=6)
        
        week, created = CommissionWeek.objects.get_or_create(
            week_number=week_number,
            year=year,
            advisor=advisor,
            defaults={
                'start_date': week_start,
                'end_date': week_end,
                'status': 'Open'
            }
        )

        # Find eligible insurance applications with status Active or Underwriter
        eligible_apps = Application.objects.filter(
            advisor=advisor,
            application_type='Insurance',
            insurance__policy_status__in=['Active', 'Underwriter'],
            commissionapplicationmapping__isnull=True
        )

        for app in eligible_apps:
            # Create mapping
            mapping = CommissionApplicationMapping(
                application=app,
                commission_week=week,
                estimated_commission=app.insurance.premium_amount * Decimal('0.2'),
                commission_rate=Decimal('20.0')
            )
            mapping.save()
            assigned_count += 1

            # Update week totals
            week.total_estimated_commission += mapping.estimated_commission
            week.save()

    messages.success(request, f'Automatically assigned {assigned_count} applications to week {week_number}.')
    return redirect('commission_weeks')

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

class AddApplicationToWeekView(ListView):
    model = Application
    template_name = 'add_application_to_week.html'
    context_object_name = 'applications'
    
    def get_queryset(self):
        self.week = get_object_or_404(CommissionWeek, pk=self.kwargs['week_id'])
        
        # Get applications that are not already mapped to any commission week
        # and are either approved or in underwriting for insurance
        queryset = Application.objects.filter(
            Q(advisor=self.request.user) | Q(advisor__isnull=True),
            application_status__in=['Approved', 'Under Review']
        ).exclude(
            commissionmapping__isnull=False
        )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['week'] = self.week
        return context
    
    def post(self, request, *args, **kwargs):
        week = get_object_or_404(CommissionWeek, pk=kwargs['week_id'])
        application_ids = request.POST.getlist('applications')
        
        for app_id in application_ids:
            application = get_object_or_404(Application, pk=app_id)
            
            # Create commission mapping
            CommissionMapping.objects.create(
                commission_week=week,
                application=application,
                commission_rate=20 if application.application_type == 'Insurance' else 0.5,
                updated_by=request.user
            )
        
        messages.success(request, f'{len(application_ids)} applications added to commission week.')
        return redirect('commission_week_detail', pk=week.pk)

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
    
class WeeklyCommissionReportView(TemplateView):
    template_name = 'crm/weekly_commission_report.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
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