"""RapidoVip URL Configuration"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.conf.urls.static import static
from graphene_django.views import GraphQLView
from django.views.decorators.csrf import csrf_exempt

from apps.users.views import Home, Login, logoutUser

urlpatterns = [
    path('admin/', admin.site.urls),
    path('users/', include(('apps.users.urls', 'users'))),
    path('comercial/', include(('apps.comercial.urls', 'comercial'))),
    path('sales/', include(('apps.sales.urls', 'sales'))),
    path('accounting/', include(('apps.accounting.urls', 'accounting'))),
    path('graphql/', csrf_exempt(GraphQLView.as_view(graphiql=True)), name='graphql'),
    path('', login_required(Home.as_view()), name='dashboard'),
    path('accounts/login/', Login.as_view(), name='login'),
    path('logout/', login_required(logoutUser), name='logout'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
