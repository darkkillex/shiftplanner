from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from rest_framework.routers import DefaultRouter
from core import views as core_views

router = DefaultRouter()
router.register(r'api/employees', core_views.EmployeeViewSet)
router.register(r'api/professions', core_views.ProfessionViewSet)
router.register(r'api/shift-types', core_views.ShiftTypeViewSet)
router.register(r'api/plans', core_views.PlanViewSet, basename='plans')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', core_views.logout_view, name='logout'),
    path('', core_views.home, name='home'),
    path('plan/<int:pk>/', core_views.monthly_plan, name='monthly_plan'),
    path('', include(router.urls)),
]
