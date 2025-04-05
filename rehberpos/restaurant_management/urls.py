"""
URL configuration for restaurant_management project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from pos.views.auth import CustomPasswordResetView, CustomPasswordResetConfirmView

urlpatterns = [
    path('admin/', admin.site.urls),
    # Kimlik doğrulama URL'leri
    path('login/', auth_views.LoginView.as_view(template_name='pos/auth/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('', include('pos.urls')),  # POS uygulaması URL'leri
    
    # Şifre sıfırlama URL'leri
    path('password-reset/', 
         CustomPasswordResetView.as_view(
             template_name='pos/auth/password_reset.html',
             email_template_name='pos/auth/password_reset_email.html',
             subject_template_name='pos/auth/password_reset_subject.txt',
             html_email_template_name='pos/auth/password_reset_email.html'
         ),
         name='password_reset'),
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='pos/auth/password_reset_done.html'
         ),
         name='password_reset_done'),
    path('reset/<uidb64>/<token>/', 
         CustomPasswordResetConfirmView.as_view(
             template_name='pos/auth/password_reset_confirm.html',
             success_url='/reset/done/'
         ),
         name='password_reset_confirm'),
    path('reset/done/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='pos/auth/password_reset_complete.html'
         ),
         name='password_reset_complete'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)  # Medya dosyaları için URL yapılandırması
