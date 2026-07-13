from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.generic.edit import FormView
from django.views.generic import TemplateView, CreateView
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponseRedirect, JsonResponse
from django.db import transaction

from .forms import (
    FormLogin, UserRegistrationForm, SubsidiaryForm, AdminUserCreateForm, AdminUserEditForm,
    SubsidiarySeriesForm, CompanyForm, CompanyEditForm,
)
from .roles import user_is_administrator
from .models import (
    Company, Subsidiary, SubsidiarySerial, CompanyUser, UserSubsidiary,
    Worker, Employee, Establishment, UserProfile, DocumentType,
)
from .subsidiary_serial_helpers import (
    ensure_service_serials,
    get_serials_for_subsidiary_company,
    serials_form_context,
    serials_table_context,
)
from .user_helpers import get_subsidiary_by_user

class Login(FormView):
    template_name = 'login.html'
    form_class = FormLogin
    success_url = reverse_lazy('dashboard')

    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return HttpResponseRedirect(self.get_success_url())
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        login(self.request, form.get_user())
        return super().form_valid(form)


def logoutUser(request):
    logout(request)
    return HttpResponseRedirect('/accounts/login/')


class Home(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['subsidiary'] = get_subsidiary_by_user(self.request.user)
        return ctx


def _get_user_assignment(user):
    subsidiary = get_subsidiary_by_user(user)
    company = None
    rol = 'O'
    full_name = user.get_full_name() or user.username
    phone = ''

    try:
        company = user.companyuser.company_rotation
    except CompanyUser.DoesNotExist:
        pass

    us = UserSubsidiary.objects.filter(user=user, subsidiary=subsidiary).first()
    if not us:
        us = UserSubsidiary.objects.filter(user=user).select_related('subsidiary').first()

    if user.is_staff:
        rol = 'A'
    elif us:
        rol = us.rol
        if not subsidiary:
            subsidiary = us.subsidiary

    worker = Worker.objects.filter(user=user).select_related('employee').last()
    if worker and worker.employee:
        full_name = worker.employee.full_name
        phone = worker.employee.phone or ''

    profile = getattr(user, 'profile', None)
    if profile and profile.phone and not phone:
        phone = profile.phone

    return {
        'subsidiary': subsidiary,
        'company': company,
        'rol': rol,
        'full_name': full_name,
        'phone': phone,
    }


def _setup_user_profile(user, form):
    subsidiary = form.cleaned_data['subsidiary']
    company = form.cleaned_data['company']
    full_name = form.cleaned_data.get('full_name', user.get_full_name() or user.username)
    names = full_name.split(' ', 2)
    rol = form.cleaned_data.get('rol', 'O')
    employee = Employee.objects.create(
        names=names[0],
        paternal_last_name=names[1] if len(names) > 1 else '',
        maternal_last_name=names[2] if len(names) > 2 else '',
        phone=form.cleaned_data.get('phone', ''),
    )
    worker = Worker.objects.create(user=user, employee=employee)
    Establishment.objects.create(worker=worker, subsidiary=subsidiary)
    CompanyUser.objects.get_or_create(user=user, defaults={'company_rotation': company})
    user.is_staff = rol == 'A'
    user.save(update_fields=['is_staff'])
    UserSubsidiary.objects.update_or_create(
        user=user, subsidiary=subsidiary,
        defaults={'rol': rol},
    )
    UserProfile.objects.get_or_create(
        user=user,
        defaults={
            'phone': form.cleaned_data.get('phone', ''),
            'subsidiary': subsidiary,
        },
    )


def _update_user_profile(user, form):
    subsidiary = form.cleaned_data['subsidiary']
    company = form.cleaned_data['company']
    full_name = form.cleaned_data.get('full_name', user.get_full_name() or user.username)
    names = full_name.split(' ', 2)
    rol = form.cleaned_data.get('rol', 'O')
    phone = form.cleaned_data.get('phone', '')

    worker = Worker.objects.filter(user=user).select_related('employee').last()
    if worker and worker.employee:
        employee = worker.employee
        employee.names = names[0]
        employee.paternal_last_name = names[1] if len(names) > 1 else ''
        employee.maternal_last_name = names[2] if len(names) > 2 else ''
        employee.phone = phone
        employee.save()
    else:
        employee = Employee.objects.create(
            names=names[0],
            paternal_last_name=names[1] if len(names) > 1 else '',
            maternal_last_name=names[2] if len(names) > 2 else '',
            phone=phone,
        )
        worker = Worker.objects.create(user=user, employee=employee)

    establishment = Establishment.objects.filter(worker=worker).last()
    if establishment:
        establishment.subsidiary = subsidiary
        establishment.save(update_fields=['subsidiary'])
    else:
        Establishment.objects.create(worker=worker, subsidiary=subsidiary)

    CompanyUser.objects.update_or_create(
        user=user,
        defaults={'company_rotation': company},
    )
    user.is_staff = rol == 'A'
    user.is_active = form.cleaned_data.get('is_active', user.is_active)
    user.save(update_fields=['is_staff', 'is_active'])

    UserSubsidiary.objects.filter(user=user).exclude(subsidiary=subsidiary).delete()
    UserSubsidiary.objects.update_or_create(
        user=user,
        subsidiary=subsidiary,
        defaults={'rol': rol},
    )

    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.phone = phone
    profile.subsidiary = subsidiary
    profile.save()


class UserListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'users/user_list.html'

    def test_func(self):
        return user_is_administrator(self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        users = User.objects.filter(
            is_superuser=False,
        ).prefetch_related(
            'usersubsidiary_set__subsidiary', 'worker_set__employee', 'companyuser__company_rotation'
        ).order_by('-date_joined')
        ctx['users'] = users
        ctx['users_active_count'] = sum(1 for u in users if u.is_active)
        ctx['users_staff_count'] = sum(1 for u in users if u.is_staff)
        return ctx


class UserCreateView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Redirige al listado; la creación se hace vía modal."""

    def test_func(self):
        return user_is_administrator(self.request.user)

    def get(self, request, *args, **kwargs):
        return redirect('users:user_list')


@login_required
@user_passes_test(user_is_administrator)
def get_user_form(request):
    if request.method != 'GET':
        return JsonResponse({'error': True}, status=405)
    from django.template import loader
    has_subsidiaries = Subsidiary.objects.filter(is_enabled=True).exists()
    has_companies = Company.objects.filter(is_enabled=True).exists()
    tpl = loader.get_template('users/user_modal_form.html')
    return JsonResponse({
        'success': True,
        'grid': tpl.render({
            'form': AdminUserCreateForm(),
            'has_subsidiaries': has_subsidiaries,
            'has_companies': has_companies,
            'can_create': has_subsidiaries and has_companies,
        }, request),
    })


@login_required
@user_passes_test(user_is_administrator)
@transaction.atomic
def save_user(request):
    if request.method != 'POST':
        return JsonResponse({'error': True}, status=405)
    form = AdminUserCreateForm(request.POST)
    if form.is_valid():
        user = form.save()
        _setup_user_profile(user, form)
        return JsonResponse({'success': True, 'message': 'Usuario registrado correctamente.'})
    errors = []
    for field, msgs in form.errors.items():
        label = form.fields[field].label if field in form.fields else field
        errors.append(f'{label}: {", ".join(msgs)}')
    return JsonResponse({'error': True, 'message': '; '.join(errors) or 'Datos inválidos'}, status=400)


@login_required
@user_passes_test(user_is_administrator)
def get_user_edit_form(request, user_id: int):
    if request.method != 'GET':
        return JsonResponse({'error': True}, status=405)
    from django.template import loader
    target_user = User.objects.get(pk=user_id)
    assignment = _get_user_assignment(target_user)
    initial = {
        'full_name': assignment['full_name'],
        'phone': assignment['phone'],
        'subsidiary': assignment['subsidiary'],
        'company': assignment['company'],
        'rol': assignment['rol'],
        'is_active': target_user.is_active,
    }
    tpl = loader.get_template('users/user_modal_edit_form.html')
    return JsonResponse({
        'success': True,
        'grid': tpl.render({
            'target_user': target_user,
            'form': AdminUserEditForm(instance=target_user, initial=initial),
        }, request),
    })


@login_required
@user_passes_test(user_is_administrator)
@transaction.atomic
def save_user_edit(request, user_id: int):
    if request.method != 'POST':
        return JsonResponse({'error': True}, status=405)
    target_user = User.objects.get(pk=user_id)
    form = AdminUserEditForm(request.POST, instance=target_user)
    if form.is_valid():
        user = form.save()
        _update_user_profile(user, form)
        return JsonResponse({'success': True, 'message': 'Usuario actualizado correctamente.'})
    errors = []
    for field, msgs in form.errors.items():
        label = form.fields[field].label if field in form.fields else field
        errors.append(f'{label}: {", ".join(msgs)}')
    return JsonResponse({'error': True, 'message': '; '.join(errors) or 'Datos inválidos'}, status=400)


class RegisterView(CreateView):
    template_name = 'users/register.html'
    form_class = UserRegistrationForm
    success_url = reverse_lazy('login')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    @transaction.atomic
    def form_valid(self, form):
        user = form.save()
        _setup_user_profile(user, form)
        return redirect(self.success_url)


@login_required
@user_passes_test(user_is_administrator)
def get_subsidiary_form(request):
    if request.method != 'GET':
        return JsonResponse({'error': True}, status=405)
    from django.template import loader
    tpl = loader.get_template('users/subsidiary_modal_form.html')
    companies = Company.objects.filter(is_enabled=True)
    return JsonResponse({
        'success': True,
        'grid': tpl.render({
            'form': SubsidiaryForm(),
            'series_form': SubsidiarySeriesForm(),
            'companies': companies,
            'has_companies': companies.exists(),
        }, request),
    })


@login_required
@user_passes_test(user_is_administrator)
def save_subsidiary(request):
    if request.method != 'POST':
        return JsonResponse({'error': True}, status=405)
    form = SubsidiaryForm(request.POST)
    series_form = SubsidiarySeriesForm(request.POST)
    if form.is_valid() and series_form.is_valid():
        subsidiary = form.save()
        data = series_form.cleaned_data
        ensure_service_serials(
            subsidiary,
            data['company'],
            serials_map={
                ('E', 'T'): data.get('serial_ticket') or '',
                ('E', 'B'): data.get('serial_boleta') or '',
                ('E', 'F'): data.get('serial_factura') or '',
                ('R', 'G'): data.get('serial_sender_guide') or '',
                ('T', 'G'): data.get('serial_carrier_guide') or '',
                ('A', 'G'): data.get('serial_cargo_manifest') or '',
                ('P', 'T'): data.get('serial_manifiesto') or '',
            },
        )
        return JsonResponse({'success': True, 'message': 'Sede registrada correctamente.'})
    errors = []
    for f in (form, series_form):
        for field, msgs in f.errors.items():
            errors.append(f'{field}: {", ".join(msgs)}')
    return JsonResponse({'error': True, 'message': '; '.join(errors) or 'Datos inválidos'}, status=400)


@login_required
@user_passes_test(user_is_administrator)
def get_subsidiary_edit_form(request, subsidiary_id: int, company_id: int):
    if request.method != 'GET':
        return JsonResponse({'error': True}, status=405)
    from django.template import loader
    subsidiary = Subsidiary.objects.get(pk=subsidiary_id)
    company = Company.objects.get(pk=company_id)
    ensure_service_serials(subsidiary, company)
    tpl = loader.get_template('users/subsidiary_modal_edit_form.html')
    return JsonResponse({
        'success': True,
        'grid': tpl.render({
            'subsidiary': subsidiary,
            'company': company,
            'form': SubsidiaryForm(instance=subsidiary),
            **serials_form_context(subsidiary, company),
        }, request),
    })


@login_required
@user_passes_test(user_is_administrator)
@transaction.atomic
def save_subsidiary_edit(request, subsidiary_id: int, company_id: int):
    if request.method != 'POST':
        return JsonResponse({'error': True}, status=405)
    subsidiary = Subsidiary.objects.select_for_update().get(pk=subsidiary_id)
    company = Company.objects.get(pk=company_id)
    ensure_service_serials(subsidiary, company)

    form = SubsidiaryForm(request.POST, instance=subsidiary)
    if not form.is_valid():
        errors = []
        for field, msgs in form.errors.items():
            errors.append(f'{field}: {", ".join(msgs)}')
        return JsonResponse({'error': True, 'message': '; '.join(errors) or 'Datos inválidos'}, status=400)

    def _val(name: str) -> str:
        return (request.POST.get(name) or '').strip()

    serial_fields = {
        ('E', 'T'): _val('serial_ticket'),
        ('E', 'B'): _val('serial_boleta'),
        ('E', 'F'): _val('serial_factura'),
        ('R', 'G'): _val('serial_sender_guide'),
        ('T', 'G'): _val('serial_carrier_guide'),
        ('A', 'G'): _val('serial_cargo_manifest'),
        ('P', 'T'): _val('serial_manifiesto'),
    }
    too_long = [
        label for label, value in (
            ('Serie tickets', serial_fields[('E', 'T')]),
            ('Serie boletas', serial_fields[('E', 'B')]),
            ('Serie facturas', serial_fields[('E', 'F')]),
            ('Serie guía remitente', serial_fields[('R', 'G')]),
            ('Serie guía transportista', serial_fields[('T', 'G')]),
            ('Serie manifiesto de carga', serial_fields[('A', 'G')]),
            ('Serie programación', serial_fields[('P', 'T')]),
        )
        if len(value) > 10
    ]
    if too_long:
        return JsonResponse(
            {'error': True, 'message': f'Campo(s) exceden 10 caracteres: {", ".join(too_long)}'},
            status=400,
        )

    form.save()
    ensure_service_serials(subsidiary, company, serials_map=serial_fields)

    return JsonResponse({'success': True, 'message': 'Sede actualizada correctamente.'})


class SubsidiaryListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'users/subsidiary_list.html'

    def test_func(self):
        return user_is_administrator(self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['subsidiaries'] = Subsidiary.objects.prefetch_related(
            'serials__company'
        ).order_by('name')

        subsidiary_rows = []
        for subsidiary in ctx['subsidiaries']:
            companies = {}
            for serial in subsidiary.serials.all():
                companies.setdefault(serial.company_id, {'company': serial.company})
                companies[serial.company_id][f'{serial.service_type}_{serial.document_type}'] = serial
            if companies:
                for company_data in companies.values():
                    company = company_data['company']
                    serial_map = get_serials_for_subsidiary_company(subsidiary, company)
                    subsidiary_rows.append({
                        'subsidiary': subsidiary,
                        'company': company,
                        'serial_groups': serials_table_context(serial_map),
                        **company_data,
                    })
            else:
                subsidiary_rows.append({'subsidiary': subsidiary, 'company': None, 'serial_groups': []})
        ctx['subsidiary_rows'] = subsidiary_rows
        ctx['companies'] = Company.objects.filter(is_enabled=True)
        ctx['form'] = SubsidiaryForm()
        ctx['series_form'] = SubsidiarySeriesForm()
        ctx['company_form'] = CompanyForm()
        ctx['has_companies'] = ctx['companies'].exists()
        return ctx


@login_required
@user_passes_test(user_is_administrator)
def create_subsidiary(request):
    if request.method == 'POST':
        form = SubsidiaryForm(request.POST)
        series_form = SubsidiarySeriesForm(request.POST)
        if form.is_valid() and series_form.is_valid():
            subsidiary = form.save()
            data = series_form.cleaned_data
            ensure_service_serials(
                subsidiary,
                data['company'],
                serials_map={
                    ('E', 'T'): data.get('serial_ticket') or '',
                    ('E', 'B'): data.get('serial_boleta') or '',
                    ('E', 'F'): data.get('serial_factura') or '',
                    ('R', 'G'): data.get('serial_sender_guide') or '',
                    ('T', 'G'): data.get('serial_carrier_guide') or '',
                    ('A', 'G'): data.get('serial_cargo_manifest') or '',
                    ('P', 'T'): data.get('serial_manifiesto') or '',
                },
            )
            return redirect('users:subsidiary_list')
    return redirect('users:subsidiary_list')


@login_required
@user_passes_test(user_is_administrator)
def create_company(request):
    if request.method == 'POST':
        form = CompanyForm(request.POST)
        if form.is_valid():
            form.save()
    return redirect('users:company_list')


class CompanyListView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'users/company_list.html'

    def test_func(self):
        return user_is_administrator(self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['companies'] = Company.objects.order_by('business_name')
        return ctx


@login_required
@user_passes_test(user_is_administrator)
def get_company_form(request):
    if request.method != 'GET':
        return JsonResponse({'error': True}, status=405)
    from django.template import loader
    tpl = loader.get_template('users/company_modal_form.html')
    return JsonResponse({
        'success': True,
        'grid': tpl.render({'form': CompanyForm()}, request),
    })


@login_required
@user_passes_test(user_is_administrator)
def save_company(request):
    if request.method != 'POST':
        return JsonResponse({'error': True}, status=405)
    form = CompanyForm(request.POST)
    if form.is_valid():
        form.save()
        return JsonResponse({'success': True, 'message': 'Empresa registrada correctamente.'})
    errors = []
    for field, msgs in form.errors.items():
        label = form.fields[field].label if field in form.fields else field
        errors.append(f'{label}: {", ".join(msgs)}')
    return JsonResponse({'error': True, 'message': '; '.join(errors) or 'Datos inválidos'}, status=400)


@login_required
@user_passes_test(user_is_administrator)
def get_company_edit_form(request, company_id: int):
    if request.method != 'GET':
        return JsonResponse({'error': True}, status=405)
    from django.template import loader
    company = Company.objects.get(pk=company_id)
    tpl = loader.get_template('users/company_modal_edit_form.html')
    return JsonResponse({
        'success': True,
        'grid': tpl.render({
            'company': company,
            'form': CompanyEditForm(instance=company),
        }, request),
    })


@login_required
@user_passes_test(user_is_administrator)
def save_company_edit(request, company_id: int):
    if request.method != 'POST':
        return JsonResponse({'error': True}, status=405)
    company = Company.objects.get(pk=company_id)
    form = CompanyEditForm(request.POST, instance=company)
    if form.is_valid():
        form.save()
        return JsonResponse({'success': True, 'message': 'Empresa actualizada correctamente.'})
    errors = []
    for field, msgs in form.errors.items():
        label = form.fields[field].label if field in form.fields else field
        errors.append(f'{label}: {", ".join(msgs)}')
    return JsonResponse({'error': True, 'message': '; '.join(errors) or 'Datos inválidos'}, status=400)


@login_required
@user_passes_test(user_is_administrator)
def toggle_user_active(request, pk):
    if request.method == 'POST':
        user = User.objects.get(pk=pk)
        if user != request.user:
            user.is_active = not user.is_active
            user.save()
    return redirect('users:user_list')


@login_required
@user_passes_test(user_is_administrator)
@transaction.atomic
def switch_subsidiary(request):
    if request.method != 'POST':
        return JsonResponse({'error': True}, status=405)
    subsidiary = Subsidiary.objects.filter(
        pk=request.POST.get('subsidiary_id'),
        is_enabled=True,
    ).first()
    if not subsidiary:
        return JsonResponse({'error': True, 'message': 'Sede no válida.'}, status=400)

    user = request.user
    UserSubsidiary.objects.update_or_create(
        user=user,
        subsidiary=subsidiary,
        defaults={'rol': 'A'},
    )
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.subsidiary = subsidiary
    profile.save(update_fields=['subsidiary'])

    worker = Worker.objects.filter(user=user).last()
    if worker:
        establishment = Establishment.objects.filter(worker=worker).last()
        if establishment:
            establishment.subsidiary = subsidiary
            establishment.save(update_fields=['subsidiary'])
        else:
            Establishment.objects.create(worker=worker, subsidiary=subsidiary)

    return JsonResponse({
        'success': True,
        'message': f'Sede activa: {subsidiary.name}',
        'subsidiary_name': subsidiary.name,
    })
