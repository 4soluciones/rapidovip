from django.urls import path
from django.contrib.auth.decorators import login_required

from .views import (
    RegisterView, SubsidiaryListView, create_subsidiary, create_company,
    UserListView, UserCreateView, toggle_user_active,
    get_user_form, save_user, get_user_edit_form, save_user_edit,
    switch_subsidiary,
    get_subsidiary_form, save_subsidiary,
    get_subsidiary_edit_form, save_subsidiary_edit,
    CompanyListView, get_company_form, save_company,
    get_company_edit_form, save_company_edit,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('list/', login_required(UserListView.as_view()), name='user_list'),
    path('create/', login_required(UserCreateView.as_view()), name='user_create'),
    path('form/', login_required(get_user_form), name='get_user_form'),
    path('save/', login_required(save_user), name='save_user'),
    path('<int:user_id>/form/', login_required(get_user_edit_form), name='get_user_edit_form'),
    path('<int:user_id>/save/', login_required(save_user_edit), name='save_user_edit'),
    path('switch-subsidiary/', login_required(switch_subsidiary), name='switch_subsidiary'),
    path('<int:pk>/toggle-active/', login_required(toggle_user_active), name='toggle_user_active'),
    path('subsidiaries/', login_required(SubsidiaryListView.as_view()), name='subsidiary_list'),
    path('subsidiaries/form/', login_required(get_subsidiary_form), name='get_subsidiary_form'),
    path('subsidiaries/save/', login_required(save_subsidiary), name='save_subsidiary'),
    path(
        'subsidiaries/<int:subsidiary_id>/company/<int:company_id>/form/',
        login_required(get_subsidiary_edit_form),
        name='get_subsidiary_edit_form',
    ),
    path(
        'subsidiaries/<int:subsidiary_id>/company/<int:company_id>/save/',
        login_required(save_subsidiary_edit),
        name='save_subsidiary_edit',
    ),
    path('subsidiaries/create/', create_subsidiary, name='create_subsidiary'),
    path('companies/', login_required(CompanyListView.as_view()), name='company_list'),
    path('companies/form/', login_required(get_company_form), name='get_company_form'),
    path('companies/save/', login_required(save_company), name='save_company'),
    path('companies/<int:company_id>/form/', login_required(get_company_edit_form), name='get_company_edit_form'),
    path('companies/<int:company_id>/save/', login_required(save_company_edit), name='save_company_edit'),
    path('companies/create/', create_company, name='create_company'),
]
