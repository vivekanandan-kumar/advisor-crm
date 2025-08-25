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
from django.contrib.auth import get_user_model  # Add this import
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.views.decorators.http import require_POST
from django.db import transaction
from decimal import Decimal
from django.views.decorators.csrf import csrf_protect
from .forms import DocumentForm, CommunicationForm
from django.db.models import Q, Count, Sum, Avg 

from .models import (
    Customer, Mortgage, InsurancePolicy, Application,
    Document, Communication, Commission
)
from .forms import (
    CustomerForm, MortgageForm, InsurancePolicyForm,
    ApplicationForm, CommunicationForm, AdvisorForm
)

# Get the custom user model
User = get_user_model()

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

class ApplicationListView(LoginRequiredMixin, ListView):
    model = Application
    template_name = 'crm/application_list.html'
    context_object_name = 'applications'
    paginate_by = 20

    def get_queryset(self):
       #return Application.objects.filter(advisor=self.request.user).order_by('-created_at')
       return Application.objects.all().order_by('-created_at')

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
    """View for insurance policy renewal alerts"""
    advisor = request.user

    # Get renewals due in different time periods
    today = timezone.now().date()
    next_7_days = today + timedelta(days=7)
    next_30_days = today + timedelta(days=30)
    next_90_days = today + timedelta(days=90)

    overdue = InsurancePolicy.objects.filter(
        advisor=advisor,
        renewal_date__lt=today,
        policy_status='Active'
    ).order_by('renewal_date')

    due_7_days = InsurancePolicy.objects.filter(
        advisor=advisor,
        renewal_date__gte=today,
        renewal_date__lte=next_7_days,
        policy_status='Active'
    ).order_by('renewal_date')

    due_30_days = InsurancePolicy.objects.filter(
        advisor=advisor,
        renewal_date__gt=next_7_days,
        renewal_date__lte=next_30_days,
        policy_status='Active'
    ).order_by('renewal_date')

    due_90_days = InsurancePolicy.objects.filter(
        advisor=advisor,
        renewal_date__gt=next_30_days,
        renewal_date__lte=next_90_days,
        policy_status='Active'
    ).order_by('renewal_date')

    context = {
        'overdue': overdue,
        'due_7_days': due_7_days,
        'due_30_days': due_30_days,
        'due_90_days': due_90_days,
    }

    return render(request, 'crm/renewal_alerts.html', context)

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

@login_required
def reports_view(request):
    """Reports and analytics view with role-based access"""
    # Determine date range (default to last 30 days)
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    # Check if user is a manager (you'll need to implement this logic)
    # For now, let's assume all users can see their own data
    is_manager = False  # You'll need to implement proper manager detection
    
    # Base queryset - filter by advisor if not manager
    if is_manager:
        # Managers see all data
        applications = Application.objects.all()
        policies = InsurancePolicy.objects.all()
        mortgages = Mortgage.objects.all()
        commissions = Commission.objects.all()
    else:
        # Regular advisors see only their data
        applications = Application.objects.filter(advisor=request.user)
        policies = InsurancePolicy.objects.filter(advisor=request.user)
        mortgages = Mortgage.objects.filter(advisor=request.user)
        commissions = Commission.objects.filter(advisor=request.user)
    
    # Calculate metrics
    total_revenue = commissions.aggregate(Sum('commission_amount'))['commission_amount__sum'] or 0
    new_policies = policies.filter(
        policy_status='Active',
        policy_start_date__gte=start_date
    ).count()
    
    # Calculate renewal rate
    active_policies = policies.filter(policy_status='Active')
    renewed_policies = policies.filter(
        policy_status='Renewed',
        renewal_date__gte=start_date,
        renewal_date__lte=end_date
    ).count()
    
    renewal_rate = (renewed_policies / active_policies.count() * 100) if active_policies.count() > 0 else 0
    
    # Calculate average commission - FIXED: Use Avg instead of Avg
    avg_commission = commissions.aggregate(Avg('commission_amount'))['commission_amount__avg'] or 0
    
    # Mortgage-specific metrics
    mortgage_applications = mortgages.filter(
        application_date__gte=start_date,
        application_date__lte=end_date
    ).count()
    
    # Additional metrics for the report
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
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'total_revenue': total_revenue,
        'new_policies': new_policies,
        'renewal_rate': renewal_rate,
        'avg_commission': avg_commission,
        'mortgage_applications': mortgage_applications,
        'avg_loan_amount': avg_loan_amount,
        'success_rate': success_rate,
        'document_status': document_status,
        'document_status_total': document_status_total,
        'policy_performance': policy_performance,
        'upcoming_renewals': upcoming_renewals,
        'user': request.user,
    }
    
    return render(request, 'crm/reports.html', context)
