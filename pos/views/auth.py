from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group, Permission
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib import messages
from django.db.models import Q
from ..forms import UserEditForm, TenantLoginForm
from ..models import Order, Table, TenantUser, Tenant
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging
from django.db import transaction

# Logger oluştur
logger = logging.getLogger(__name__)

def create_default_groups():
    """Varsayılan kullanıcı gruplarını oluştur"""
    # Garson grubu
    waiter_group, _ = Group.objects.get_or_create(name='Garson')
    waiter_permissions = Permission.objects.filter(
        Q(codename__contains='add_order') |
        Q(codename__contains='change_order') |
        Q(codename__contains='view_order') |
        Q(codename__contains='view_product')
    )
    waiter_group.permissions.set(waiter_permissions)
    
    # Kasiyer grubu
    cashier_group, _ = Group.objects.get_or_create(name='Kasiyer')
    cashier_permissions = Permission.objects.filter(
        Q(codename__contains='add_payment') |
        Q(codename__contains='change_payment') |
        Q(codename__contains='view_payment') |
        Q(codename__contains='view_order')
    )
    cashier_group.permissions.set(cashier_permissions)
    
    # Mutfak grubu
    kitchen_group, _ = Group.objects.get_or_create(name='Mutfak')
    kitchen_permissions = Permission.objects.filter(
        Q(codename__contains='view_order') |
        Q(codename__contains='change_order')
    )
    kitchen_group.permissions.set(kitchen_permissions)

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            try:
                # Kullanıcıyı oluştur
                user = form.save(commit=False)
                
                # Form'dan gelen ek bilgileri kaydet
                user.first_name = request.POST.get('first_name', '')
                user.email = request.POST.get('email', '')
                
                # Her kullanıcıyı admin yap
                user.is_superuser = True
                user.is_staff = True
                
                user.save()
                
                # Kullanıcıyı otomatik olarak giriş yap
                login(request, user)
                return redirect('pos:index')
            except Exception as e:
                form.add_error(None, str(e))
    
    return render(request, 'pos/auth/register.html')


def user_login(request):
    if request.method == 'POST':
        login_type = request.POST.get('login_type')
        username = request.POST.get('username')
        password = request.POST.get('password')
        tenant_name = request.POST.get('tenant_name')

        if login_type == 'owner':
            user = authenticate(username=username, password=password)
            if user is not None:
                if user.is_active:
                    # İşletme sahibi kontrolü
                    tenant_user = TenantUser.objects.filter(user=user, role='owner').first()
                    if tenant_user:
                        login(request, user)
                        return redirect('pos:dashboard')
                    else:
                        messages.error(request, 'Bu hesap bir işletme sahibine ait değil.')
                else:
                    messages.error(request, 'Hesabınız aktif değil.')
            else:
                messages.error(request, 'Kullanıcı adı veya şifre hatalı.')
        
        elif login_type == 'employee':
            if not tenant_name:
                messages.error(request, 'İşletme adı gerekli.')
                return render(request, 'pos/auth/login.html')

            # İşletmeyi bul
            tenant = Tenant.objects.filter(name=tenant_name).first()
            if not tenant:
                messages.error(request, 'Belirtilen isimde bir işletme bulunamadı.')
                return render(request, 'pos/auth/login.html')

            user = authenticate(username=username, password=password)
            if user is not None:
                if user.is_active:
                    # Personel kontrolü
                    tenant_user = TenantUser.objects.filter(
                        user=user,
                        tenant=tenant,
                        role='staff'
                    ).first()
                    
                    if tenant_user:
                        login(request, user)
                        return redirect('pos:dashboard')
                    else:
                        messages.error(request, 'Bu kullanıcı belirtilen işletmede personel olarak kayıtlı değil.')
                else:
                    messages.error(request, 'Hesabınız aktif değil.')
            else:
                messages.error(request, 'Kullanıcı adı veya şifre hatalı.')

    return render(request, 'pos/auth/login.html')

@login_required
def user_list(request):
    # Varsayılan grupları oluştur
    create_default_groups()
    
    # Mevcut işletmeyi al
    tenant = getattr(request, 'tenant', None)
    
    if request.user.is_superuser and not tenant:
        # Süper kullanıcı ise ve herhangi bir işletmeye sahip değilse tüm kullanıcıları görebilir
        users = User.objects.all().prefetch_related('groups')
    elif tenant:
        # İşletmeye bağlı kullanıcıları ve işletme sahibini göster
        # TenantUser modelini kullanarak bu tenant'a bağlı tüm kullanıcıları alalım
        tenant_user_ids = TenantUser.objects.filter(
            tenant=tenant, 
            is_active=True
        ).values_list('user_id', flat=True)
        
        users = User.objects.filter(
            Q(id=tenant.owner_id) |  # İşletme sahibi
            Q(id__in=tenant_user_ids)  # TenantUser tablosunda kayıtlı kullanıcılar
        ).prefetch_related('groups', 'tenant_memberships').distinct()
    else:
        # Admin veya tenant olmayan kullanıcı için sadece kendi kullanıcısını göster
        users = User.objects.filter(id=request.user.id).prefetch_related('groups')
    
    # Her kullanıcının işletmedeki rolünü bulalım
    user_roles = {}
    if tenant:
        for user in users:
            # İşletme sahibi mi?
            if user.id == tenant.owner_id:
                user_roles[user.id] = "İşletme Sahibi"
            else:
                # TenantUser tablosundan rolünü alalım
                try:
                    tenant_user = TenantUser.objects.get(tenant=tenant, user=user)
                    user_roles[user.id] = tenant_user.get_role_display()
                except TenantUser.DoesNotExist:
                    user_roles[user.id] = "Belirsiz"
    
    return render(request, 'pos/user_list.html', {
        'users': users,
        'user_roles': user_roles,
    })

@login_required
def user_create(request):
    # Mevcut tenant'ı kontrol et
    tenant = getattr(request, 'tenant', None)
    
    if request.method == 'POST':
        form = UserEditForm(request.POST, tenant=tenant)
        if form.is_valid():
            try:
                user = form.save(commit=False)
                user.is_staff = True  # Personel erişimi için gerekli
                user.save()
                
                # Django gruplarını rollere göre otomatik ayarla
                tenant_role = form.cleaned_data.get('tenant_role')
                groups_to_add = []
                
                # Rol bazlı grup ataması
                if tenant_role == 'waiter':
                    waiter_group, _ = Group.objects.get_or_create(name='Garson')
                    groups_to_add.append(waiter_group)
                elif tenant_role == 'cashier':
                    cashier_group, _ = Group.objects.get_or_create(name='Kasiyer')
                    groups_to_add.append(cashier_group)
                elif tenant_role == 'kitchen':
                    kitchen_group, _ = Group.objects.get_or_create(name='Mutfak')
                    groups_to_add.append(kitchen_group)
                elif tenant_role in ['manager', 'owner']:
                    # Yöneticilere tüm grupları ekleyelim
                    waiter_group, _ = Group.objects.get_or_create(name='Garson')
                    cashier_group, _ = Group.objects.get_or_create(name='Kasiyer')
                    kitchen_group, _ = Group.objects.get_or_create(name='Mutfak')
                    groups_to_add.extend([waiter_group, cashier_group, kitchen_group])
                
                # Grupları kullanıcıya ekle
                user.groups.set(groups_to_add)
                
                # TenantUser ilişkisini kur
                if tenant:
                    tenant_user, created = TenantUser.objects.update_or_create(
                        user=user,
                        tenant=tenant,
                        defaults={'role': tenant_role, 'is_active': True}
                    )
                
                messages.success(request, 'Kullanıcı başarıyla oluşturuldu.')
                return redirect('pos:user_list')
            except Exception as e:
                messages.error(request, f'Kullanıcı oluşturulurken bir hata oluştu: {str(e)}')
        else:
            # Form geçersizse hata mesajlarını göster
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = UserEditForm(tenant=tenant)
    
    context = {
        'form': form,
        'user_obj': None,  # Yeni kullanıcı olduğu için None
        'tenant': tenant,  # Template'e tenant bilgisini geçir
    }
    return render(request, 'pos/user_form.html', context)

@login_required
def user_edit(request, user_id):
    # Mevcut tenant'ı al
    tenant = getattr(request, 'tenant', None)
    
    # İlk önce kullanıcıyı bul
    user = get_object_or_404(User, id=user_id)
    
    # Kullanıcının o tenant'a ait olup olmadığını kontrol et
    if tenant:
        try:
            # TenantUser tablosunda ilişki var mı kontrol et
            tenant_user = TenantUser.objects.get(tenant=tenant, user=user)
        except TenantUser.DoesNotExist:
            # İşletme sahibi mi kontrol et
            if tenant.owner != user and user.id != request.user.id:
                messages.error(request, 'Bu kullanıcıyı düzenleme yetkiniz yok.')
                return redirect('pos:user_list')
    
    if request.method == 'POST':
        # İsteği kopyala ve mevcut grupları ve yetkiyi koru
        post_data = request.POST.copy()
        # Kullanıcı adını değiştirme
        post_data['username'] = user.username
        # Superuser durumunu koru
        post_data['is_superuser'] = user.is_superuser
        # Mevcut grupları koru
        post_data.setlist('groups', [g.id for g in user.groups.all()])
        
        form = UserEditForm(post_data, instance=user, tenant=tenant)
            
        if form.is_valid():
            form.save()
            messages.success(request, 'Kullanıcı bilgileri başarıyla güncellendi.')
            return redirect('pos:user_list')
    else:
        form = UserEditForm(instance=user, tenant=tenant)
    
    context = {
        'form': form,
        'user_obj': user
    }
    return render(request, 'pos/user_form.html', context)

@login_required
def user_delete(request, user_id):
    # Mevcut tenant'ı al
    tenant = getattr(request, 'tenant', None)
    
    # İlk önce kullanıcıyı bul
    user = get_object_or_404(User, id=user_id)
    
    # Kullanıcının o tenant'a ait olup olmadığını kontrol et
    if tenant and not request.user.is_superuser:
        # Kullanıcı işletme sahibi mi?
        is_owner = (user.id == tenant.owner_id)
        
        # İşletme sahibi silinemez
        if is_owner:
            messages.error(request, 'İşletme sahibi silinemez.')
            return redirect('pos:user_list')
        
        # İşletmeye ait değilse erişimi reddet
        try:
            tenant_user = TenantUser.objects.get(tenant=tenant, user=user)
        except TenantUser.DoesNotExist:
            messages.error(request, 'Bu kullanıcıyı silme yetkiniz yok.')
            return redirect('pos:user_list')
    
    # Kendini silmeye çalışıyorsa engelle
    if user.id == request.user.id:
        messages.error(request, 'Kendi hesabınızı silemezsiniz.')
        return redirect('pos:user_list')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Önce TenantUser ilişkilerini sil
                TenantUser.objects.filter(user=user).delete()
                
                # Kullanıcıyı sil
                user.delete()
                
                messages.success(request, 'Kullanıcı başarıyla silindi.')
                return redirect('pos:user_list')
        except Exception as e:
            messages.error(request, f'Kullanıcı silinirken bir hata oluştu: {str(e)}')
            return redirect('pos:user_list')
    
    return render(request, 'pos/user_confirm_delete.html', {'user': user})

@login_required
def select_tenant(request):
    """Kullanıcının bağlı olduğu işletmeler arasından seçim yapmasını sağlar"""
    # İşletme sahibi olduğu tenant'ı ekleyelim
    try:
        owned_tenant = request.user.owned_tenant
        owned = True
    except Tenant.DoesNotExist:
        owned_tenant = None
        owned = False
    
    # Çalışan olarak bağlı olduğu tenant'ları alalım
    tenant_memberships = TenantUser.objects.filter(
        user=request.user, 
        is_active=True
    ).select_related('tenant')
    
    if request.method == 'POST':
        tenant_id = request.POST.get('tenant_id')
        if tenant_id:
            # Geçerli bir tenant_id gönderildi mi kontrol et
            try:
                tenant_id = int(tenant_id)
                # Kullanıcının bu tenant'a erişimi var mı kontrol et
                if owned and owned_tenant.id == tenant_id:
                    # İşletme sahibi olduğu tenant
                    request.session['tenant_id'] = tenant_id
                    return redirect('pos:index')
                elif tenant_memberships.filter(tenant_id=tenant_id).exists():
                    # Çalışan olarak bağlı olduğu tenant
                    request.session['tenant_id'] = tenant_id
                    return redirect('pos:index')
                else:
                    messages.error(request, 'Bu işletmeye erişim yetkiniz yok.')
            except (ValueError, Tenant.DoesNotExist):
                messages.error(request, 'Geçersiz işletme seçimi.')
        else:
            messages.error(request, 'Lütfen bir işletme seçin.')
    
    context = {
        'owned_tenant': owned_tenant,
        'tenant_memberships': tenant_memberships,
    }
    return render(request, 'pos/auth/select_tenant.html', context)

@login_required
def logout_view(request):
    """
    Kullanıcı çıkışını sağlar ve session'ı temizler.
    """
    # Session'dan tenant ID ve rol bilgisini temizle
    if 'current_tenant_id' in request.session:
        del request.session['current_tenant_id']
    if 'user_role' in request.session:
        del request.session['user_role']
        
    # Çıkış yap
    logout(request)
    messages.success(request, 'Başarıyla çıkış yaptınız.')
    return redirect('pos:login')

class CustomPasswordResetView(PasswordResetView):
    email_template_name = 'pos/auth/password_reset_email.html'
    subject_template_name = 'pos/auth/password_reset_subject.txt'
    html_email_template_name = 'pos/auth/password_reset_email.html'
    success_url = '/password-reset/done/'

    def form_valid(self, form):
        """Form geçerli olduğunda çalışır"""
        email = form.cleaned_data["email"]
        logger.info(f"Şifre sıfırlama talebi alındı: {email}")
        
        # Kullanıcıyı bul
        users = self.get_users(email)
        if not any(users):
            logger.warning(f"Şifre sıfırlama için kullanıcı bulunamadı: {email}")
            # Kullanıcı bulunamasa bile başarılı gibi göster (güvenlik için)
            return super().form_valid(form)
        
        try:
            result = super().form_valid(form)
            logger.info(f"Şifre sıfırlama e-postası başarıyla gönderildi: {email}")
            return result
        except Exception as e:
            logger.error(f"Şifre sıfırlama e-postası gönderilirken hata oluştu: {str(e)}")
            raise

    def get_users(self, email):
        """E-posta adresine göre kullanıcıları getir"""
        active_users = User.objects.filter(
            email__iexact=email,
            is_active=True
        )
        users = [u for u in active_users if u.has_usable_password()]
        logger.info(f"Bulunan aktif kullanıcı sayısı: {len(users)}")
        return users

    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email, to_email, html_email_template_name=None):
        """E-posta gönderme işlemi"""
        try:
            subject = render_to_string(subject_template_name, context)
            subject = ''.join(subject.splitlines())
            
            html_message = render_to_string(html_email_template_name or email_template_name, context)
            plain_message = strip_tags(html_message)
            
            from_email = from_email or None
            
            logger.info(f"E-posta gönderiliyor: {to_email}")
            logger.debug(f"E-posta içeriği: {plain_message[:100]}...")
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=from_email,
                recipient_list=[to_email],
                html_message=html_message,
                fail_silently=False,
            )
            logger.info(f"E-posta başarıyla gönderildi: {to_email}")
            
        except Exception as e:
            logger.error(f"E-posta gönderilirken hata oluştu: {str(e)}")
            raise

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    def form_valid(self, form):
        user = form.save()
        logger.info(f"Kullanıcı şifresi başarıyla değiştirildi: {user.username}")
        messages.success(self.request, 'Şifreniz başarıyla değiştirildi!')
        return super().form_valid(form)

    def form_invalid(self, form):
        logger.warning(f"Şifre değiştirme formu geçersiz: {form.errors}")
        for error in form.errors.values():
            messages.error(self.request, error)
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.validlink:
            logger.info("Geçerli şifre sıfırlama bağlantısı")
        else:
            logger.warning("Geçersiz şifre sıfırlama bağlantısı")
        return context 