from django.core.exceptions import ObjectDoesNotExist

from .models import Subsidiary, UserSubsidiary, Worker, Establishment


def get_subsidiary_by_user(user_obj):
    # Preferencia activa (switch_subsidiary); UserSubsidiary solo indica acceso/rol.
    try:
        subsidiary = user_obj.profile.subsidiary
    except ObjectDoesNotExist:
        subsidiary = None
    if subsidiary:
        return subsidiary

    worker = Worker.objects.filter(user=user_obj).select_related('employee').last()
    if worker:
        establishment = Establishment.objects.filter(worker=worker).select_related('subsidiary').last()
        if establishment:
            return establishment.subsidiary
    user_subsidiary = UserSubsidiary.objects.filter(user=user_obj).select_related('subsidiary').first()
    if user_subsidiary:
        return user_subsidiary.subsidiary
    return Subsidiary.objects.filter(is_enabled=True).first()
