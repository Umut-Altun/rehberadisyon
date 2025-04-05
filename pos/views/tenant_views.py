from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.db import transaction
from django.urls import reverse
from django.contrib.auth import logout

from ..models import Tenant, Category, Order, OrderItem, Payment, Table, Product, Customer, TenantUser
from ..forms import TenantForm, UserRegistrationForm

@login_required
def tenant_detail(request):
    """
    İşletme bilgilerini gösterme
    """
    try:
        tenant = getattr(request.user, 'owned_tenant', None)
        if not tenant:
            # Middleware tarafından atanan tenant kontrolü
            tenant = getattr(request, 'tenant', None)
            if not tenant:
                messages.warning(request, 'Henüz bir işletme oluşturmamışsınız.')
                return redirect('pos:tenant_create')
        return render(request, 'pos/tenant/tenant_detail.html', {'tenant': tenant})
    except Tenant.DoesNotExist:
        messages.warning(request, 'Henüz bir işletme oluşturmamışsınız.')
        return redirect('pos:tenant_create')

@login_required
def tenant_create(request):
    """
    Yeni işletme oluşturma
    """
    # Kullanıcının zaten bir işletmesi varsa detay sayfasına yönlendir
    try:
        if hasattr(request.user, 'tenant'):
            messages.info(request, 'Zaten bir işletmeniz bulunmaktadır.')
            return redirect('pos:tenant_detail')
    except Tenant.DoesNotExist:
        pass
    
    if request.method == 'POST':
        form = TenantForm(request.POST, request.FILES)
        if form.is_valid():
            tenant = form.save(commit=False)
            tenant.owner = request.user
            tenant.save()
            messages.success(request, 'İşletmeniz başarıyla oluşturuldu!')
            return redirect('pos:tenant_detail')
    else:
        form = TenantForm()
    
    return render(request, 'pos/tenant/tenant_form.html', {'form': form, 'title': 'Yeni İşletme Oluştur'})

@login_required
def tenant_edit(request):
    """
    İşletme bilgilerini düzenleme
    """
    try:
        tenant = getattr(request.user, 'owned_tenant', None)
        if not tenant:
            # Middleware tarafından atanan tenant kontrolü
            tenant = getattr(request, 'tenant', None)
            if not tenant:
                messages.warning(request, 'Henüz bir işletme oluşturmamışsınız.')
                return redirect('pos:tenant_create')
    except Tenant.DoesNotExist:
        messages.warning(request, 'Henüz bir işletme oluşturmamışsınız.')
        return redirect('pos:tenant_create')
        
    if request.method == 'POST':
        form = TenantForm(request.POST, request.FILES, instance=tenant)
        if form.is_valid():
            form.save()
            messages.success(request, 'İşletme bilgileriniz güncellendi!')
            return redirect('pos:tenant_detail')
    else:
        form = TenantForm(instance=tenant)
    
    return render(request, 'pos/tenant/tenant_form.html', {'form': form, 'title': 'İşletme Bilgilerini Düzenle'})

@login_required
def tenant_delete(request):
    """
    İşletme silme işlemi
    """
    try:
        tenant = getattr(request.user, 'owned_tenant', None)
        if not tenant:
            messages.error(request, 'Silinecek işletme bulunamadı.')
            return redirect('pos:tenant_detail')
            
        # Form'dan gelen doğrulama kontrolü
        confirm_delete = request.POST.get('confirm_delete', '')
        if confirm_delete != tenant.name:
            messages.error(request, 'İşletme adı doğru yazılmadı. Silme işlemi iptal edildi.')
            return redirect('pos:tenant_detail')
        
        # Mevcut kullanıcı referansını sakla
        current_user = request.user
            
        # Kademeli silme işlemi
        with transaction.atomic():
            # Tüm ilişkili modelleri sil - BaseModel'den türeyen herşey
            Payment.objects.filter(tenant=tenant).delete()
            OrderItem.objects.filter(tenant=tenant).delete() 
            Order.objects.filter(tenant=tenant).delete()
            Product.objects.filter(tenant=tenant).delete()
            Category.objects.filter(tenant=tenant).delete()
            Customer.objects.filter(tenant=tenant).delete()
            Table.objects.filter(tenant=tenant).delete()
            
            # TenantUser ilişkilerini sil ve ilişkili kullanıcıları bul
            tenant_users = TenantUser.objects.filter(tenant=tenant)
            user_ids = list(tenant_users.values_list('user_id', flat=True))
            tenant_users.delete()
            
            # İşletmeye bağlı tüm kullanıcıları sil (işletme sahibi hariç)
            User.objects.filter(id__in=user_ids).delete()
            
            # İşletmeyi sil
            tenant.delete()
            
            # Kullanıcıyı logout yap
            logout(request)
            
            # Kullanıcı hesabını sil
            current_user.delete()
            
            messages.success(request, 'İşletme ve tüm ilişkili kullanıcı hesapları başarıyla silindi.')
            return redirect('login')
        
    except Exception as e:
        messages.error(request, f'İşletme silinirken bir hata oluştu: {str(e)}')
        return redirect('pos:tenant_detail')

def register(request):
    """
    Yeni kullanıcı kaydı ve işletme oluşturma (birlikte)
    """
    if request.method == 'POST':
        user_form = UserRegistrationForm(request.POST)
        tenant_form = TenantForm(request.POST, request.FILES)
        
        if user_form.is_valid() and tenant_form.is_valid():
            with transaction.atomic():
                # Kullanıcı oluştur
                user = user_form.save()
                
                # İşletme oluştur
                tenant = tenant_form.save(commit=False)
                tenant.owner = user
                tenant.save()
                
                messages.success(request, 'Kaydınız başarıyla oluşturuldu! Şimdi giriş yapabilirsiniz.')
                return redirect('pos:login')
    else:
        user_form = UserRegistrationForm()
        tenant_form = TenantForm()
    
    return render(request, 'pos/tenant/register.html', {
        'user_form': user_form,
        'tenant_form': tenant_form
    }) 