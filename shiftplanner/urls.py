from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.contrib.admin import AdminSite
from django.contrib import admin as django_admin

from rest_framework.routers import DefaultRouter

from core import views as core_views, views
from core.views_misc import changelog_view

router = DefaultRouter()
router.register(r'api/employees', core_views.EmployeeViewSet)
router.register(r'api/professions', core_views.ProfessionViewSet)
router.register(r'api/shift-types', core_views.ShiftTypeViewSet)
router.register(r'api/plans', core_views.PlanViewSet, basename='plans')
router.register(r'api/reminders', core_views.ReminderViewSet)

class SuperuserOnlyAdmin(AdminSite):
    site_header = "Shift Planner — Admin"
    site_title = "Shift Planner — Admin"
    index_title = "Dashboard"
    def has_permission(self, request):
        return request.user.is_active and request.user.is_superuser

superadmin = SuperuserOnlyAdmin(name='superadmin')

# registra tutti i ModelAdmin già registrati sul default admin
for model, model_admin in list(django_admin.site._registry.items()):
    superadmin._registry[model] = model_admin


urlpatterns = [
    path('admin/', superadmin.urls),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', core_views.logout_view, name='logout'),
    path('', core_views.home, name='home'),
    path('plan/<int:pk>/', core_views.monthly_plan, name='monthly_plan'),
    path('', include(router.urls)),
    path('profile/', core_views.profile, name='profile'),
    path('password_change/', auth_views.PasswordChangeView.as_view(
        template_name='password_change.html'
    ), name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='password_change_done.html'
    ), name='password_change_done'),
    path("plans/new/", views.plan_create, name="plan_create"),
    path("changelog/", changelog_view, name="changelog"),
    path("templates/new/", core_views.template_create, name="template_create"),
    path("templates/<int:pk>/", core_views.template_detail, name="template_detail"),
    path("funzioni/", views.functions_hub, name="functions"),
    path("piani/", views.plans_area, name="plans_area"),
    path("template-piani/", views.templates_area, name="templates_area"),
    path('api/templates/<int:pk>/insert_row/', core_views.template_insert_row, name='template-insert-row'),
]
