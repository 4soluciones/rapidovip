from .models import UserSubsidiary

ROLE_ADMIN = 'A'
ROLE_OPERATOR = 'O'

ROLE_CHOICES = (
    (ROLE_ADMIN, 'Administrador'),
    (ROLE_OPERATOR, 'Operador'),
)

ROLE_LABELS = dict(ROLE_CHOICES)


def get_user_role(user):
    """Devuelve el rol efectivo del usuario (A=Administrador, O=Operador)."""
    if not user.is_authenticated:
        return None

    if user.is_staff:
        return ROLE_ADMIN

    roles = list(UserSubsidiary.objects.filter(user=user).values_list('rol', flat=True))
    if ROLE_ADMIN in roles:
        return ROLE_ADMIN
    if roles:
        role = roles[0]
        if role == 'E':
            return ROLE_OPERATOR
        return role
    return ROLE_OPERATOR


def user_is_administrator(user):
    return get_user_role(user) == ROLE_ADMIN


def user_is_operator(user):
    return get_user_role(user) == ROLE_OPERATOR
