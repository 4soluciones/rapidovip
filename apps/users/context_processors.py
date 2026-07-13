from .models import Company, CompanyUser, Subsidiary
from .roles import get_user_role, user_is_administrator, ROLE_LABELS
from .user_helpers import get_subsidiary_by_user


def user_context(request):
    company_rotation = None
    current_subsidiary = None
    subsidiary_name = ''
    display_name = ''
    user_role = None
    can_see_reports = False
    can_see_admin = False
    all_subsidiaries = []

    if request.user.is_authenticated:
        display_name = request.user.get_full_name() or request.user.username
        user_role = get_user_role(request.user)
        can_see_reports = user_is_administrator(request.user)
        can_see_admin = user_is_administrator(request.user)

        try:
            company_rotation = request.user.companyuser.company_rotation
        except CompanyUser.DoesNotExist:
            company = Company.objects.filter(is_enabled=True).first()
            if company:
                CompanyUser.objects.get_or_create(
                    user=request.user,
                    defaults={'company_rotation': company},
                )
                company_rotation = company

        current_subsidiary = get_subsidiary_by_user(request.user)
        if current_subsidiary:
            subsidiary_name = current_subsidiary.name

        worker = getattr(request.user, 'worker_set', None)
        if worker and worker.exists():
            w = worker.last()
            if w and w.employee:
                display_name = w.employee.full_name

        if can_see_admin:
            all_subsidiaries = Subsidiary.objects.filter(is_enabled=True).order_by('name')

    return {
        'company_rotation': company_rotation,
        'current_subsidiary': current_subsidiary,
        'user_display_name': display_name,
        'user_subsidiary_name': subsidiary_name,
        'user_role': user_role,
        'user_role_display': ROLE_LABELS.get(user_role, ''),
        'can_see_reports': can_see_reports,
        'can_see_admin': can_see_admin,
        'all_subsidiaries': all_subsidiaries,
    }
