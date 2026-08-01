from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from predictor import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('predictor.urls')),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='predictor/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
]
