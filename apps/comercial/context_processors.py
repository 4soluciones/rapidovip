from apps.users.models import Company


def companies(request):
    all_companies = Company.objects.all()
    return {
        'all_companies': all_companies,
    }