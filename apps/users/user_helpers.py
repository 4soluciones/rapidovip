from .models import Subsidiary, UserSubsidiary, Worker, Establishment


def get_subsidiary_by_user(user_obj):
    worker = Worker.objects.filter(user=user_obj).select_related('employee').last()
    if worker:
        establishment = Establishment.objects.filter(worker=worker).select_related('subsidiary').last()
        if establishment:
            return establishment.subsidiary
    user_subsidiary = UserSubsidiary.objects.filter(user=user_obj).select_related('subsidiary').first()
    if user_subsidiary:
        return user_subsidiary.subsidiary
    if hasattr(user_obj, 'profile') and user_obj.profile.subsidiary:
        return user_obj.profile.subsidiary
    return Subsidiary.objects.filter(is_enabled=True).first()
