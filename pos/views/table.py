from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from ..models import Table, Order, Product, OrderItem
from django.utils import timezone
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.contrib import messages
from django.urls import reverse

@login_required
def index(request):
    tables = Table.objects.all()
    active_orders = Order.objects.filter(status__in=['pending', 'preparing'])
    context = {
        'tables': tables,
        'active_orders': active_orders
    }
    return render(request, 'pos/index.html', context)

@login_required
def table_list(request):
    # Kullanıcının tenant'ını bul
    tenant = None
    try:
        tenant = request.user.owned_tenant
    except:
        tenant_membership = request.user.tenant_memberships.first()
        if tenant_membership:
            tenant = tenant_membership.tenant
    
    if not tenant:
        messages.error(request, 'Herhangi bir işletmeye bağlı değilsiniz. Lütfen sistem yöneticisi ile iletişime geçin.')
        return redirect('pos:index')
        
    tables = Table.objects.filter(tenant=tenant).order_by('floor', 'number')
    return render(request, 'pos/table_list.html', {'tables': tables})

@login_required
def table_detail(request, table_id):
    table = get_object_or_404(Table, id=table_id)
    products = Product.objects.filter(is_available=True).order_by('category', 'name')
    
    active_order = Order.objects.filter(
        table=table,
        status__in=['pending', 'preparing']
    ).prefetch_related('items__product').order_by('-created_at').first()
    
    if request.method == 'POST':
        try:
            product_id = request.POST.get('product')
            quantity = request.POST.get('quantity', 1)
            notes = request.POST.get('notes', '')
            
            product = Product.objects.get(id=product_id)
            
            order = Order.objects.create(
                table=table,
                staff=request.user,
                status='pending'
            )
            
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=quantity,
                notes=notes
            )
            
            if not table.is_occupied:
                table.is_occupied = True
                table.save()
            
            return redirect('pos:table_detail', table_id=table.id)
            
        except Exception as e:
            return redirect('pos:table_detail', table_id=table_id)
    
    context = {
        'table': table,
        'products': products,
        'active_order': active_order,
    }
    return render(request, 'pos/table_detail.html', context)

@login_required
def table_create(request):
    if request.method == 'POST':
        number = request.POST.get('number')
        capacity = request.POST.get('capacity')
        floor = request.POST.get('floor')
        
        # AJAX isteği mi kontrol et
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        # Önce kullanıcının tenant ilişkilerini kontrol et
        tenant = None
        
        # 1. İşletme sahibi mi kontrol et
        try:
            tenant = request.user.owned_tenant
        except:
            # 2. İşletme üyesi mi kontrol et
            tenant_membership = request.user.tenant_memberships.first()
            if tenant_membership:
                tenant = tenant_membership.tenant
        
        if not tenant:
            if is_ajax:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Herhangi bir işletmeye bağlı değilsiniz.'
                })
            messages.error(request, 'Herhangi bir işletmeye bağlı değilsiniz. Lütfen sistem yöneticisi ile iletişime geçin.')
            return redirect("pos:table_management")
        
        # Aynı numaralı masa var mı kontrol et
        try:
            existing_table = Table.objects.get(tenant=tenant, number=number)
            error_message = f'Bu masa numarası zaten kullanılmaktadır (Masa {number}).'
            
            if is_ajax:
                return JsonResponse({
                    'status': 'error',
                    'message': error_message
                })
                
            messages.error(request, error_message)
            return redirect("pos:table_management")
        except Table.DoesNotExist:
            # Masa yoksa devam et
            pass
            
        try:
            # İlk olarak aynı numaralı masa için bir kez daha kontrol yapalım
            if Table.objects.filter(tenant=tenant, number=number).exists():
                error_message = f'Bu masa numarası zaten kullanılmaktadır (Masa {number}).'
                
                if is_ajax:
                    return JsonResponse({
                        'status': 'error',
                        'message': error_message
                    })
                    
                messages.error(request, error_message)
                return redirect("pos:table_management")
                
            # Yeni masayı oluşturalım
            table = Table.objects.create(
                tenant=tenant,
                number=number,
                capacity=capacity,
                floor=floor
            )
            
            if is_ajax:
                return JsonResponse({
                    'status': 'success',
                    'message': f'Masa {number} başarıyla oluşturuldu.',
                    'redirect_url': reverse('pos:table_management')
                })
                
            messages.success(request, f'Masa {number} başarıyla oluşturuldu.')
            return redirect('pos:table_management')
        except Exception as e:
            error_message = f'Masa oluşturulurken bir hata oluştu: {str(e)}'
            
            if is_ajax:
                return JsonResponse({
                    'status': 'error',
                    'message': error_message
                })
                
            messages.error(request, error_message)
            return redirect("pos:table_management")
    
    return render(request, "pos/table_create.html")

@login_required
def table_edit(request, table_id):
    # Masa düzenleme işlevi devre dışı bırakıldı
    messages.warning(request, "Masa düzenleme işlevi devre dışı bırakılmıştır.")
    return redirect('pos:table_management')

@login_required
def table_delete(request, table_id):
    # Tabloyu bul veya 404 döndür
    table = get_object_or_404(Table, id=table_id)
    
    # AJAX isteği mi kontrol et
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if request.method == 'POST':
        # Masa durumunu kontrol et
        if table.is_occupied:
            error_message = f'Masa {table.number} şu anda dolu olduğu için silinemez. Önce masayı boşaltın.'
            
            if is_ajax:
                return JsonResponse({
                    'status': 'error',
                    'message': error_message
                })
                
            messages.error(request, error_message)
            return redirect('pos:table_management')
        
        try:
            table_number = table.number
            table.delete()
            
            if is_ajax:
                return JsonResponse({
                    'status': 'success',
                    'message': f'Masa {table_number} başarıyla silindi.',
                    'redirect_url': reverse('pos:table_management')
                })
                
            messages.success(request, f'Masa {table_number} başarıyla silindi.')
            return redirect('pos:table_management')
        except Exception as e:
            error_message = f'Masa silinirken bir hata oluştu: {str(e)}'
            
            if is_ajax:
                return JsonResponse({
                    'status': 'error',
                    'message': error_message
                })
                
            messages.error(request, error_message)
            return redirect('pos:table_management')
            
    # GET isteği - silme sayfasını göster
    return render(request, 'pos/table_confirm_delete.html', {'table': table})

@login_required
def table_transfer(request):
    if request.method == 'POST':
        source_table_id = request.POST.get('source_table')
        target_table_id = request.POST.get('target_table')
        
        # AJAX isteği mi kontrol et
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        try:
            source_table = Table.objects.get(id=source_table_id)
            target_table = Table.objects.get(id=target_table_id)
            
            # Aktif siparişleri transfer et
            active_orders = Order.objects.filter(
                table=source_table,
                status__in=['pending', 'preparing']
            )
            
            # Taşınacak sipariş var mı kontrol et
            if not active_orders.exists():
                if is_ajax:
                    return JsonResponse({
                        'status': 'error', 
                        'message': 'Taşınacak aktif sipariş bulunamadı.'
                    })
                return redirect('pos:table_list')
            
            order_count = 0
            for order in active_orders:
                order.table = target_table
                order.save()
                order_count += 1
            
            # Masa durumlarını güncelle
            source_table.is_occupied = False
            source_table.save()
            
            target_table.is_occupied = True
            target_table.save()
            
            # AJAX isteği için JSON yanıtı
            if is_ajax:
                return JsonResponse({
                    'status': 'success',
                    'message': f'Masa {source_table.number}\'den Masa {target_table.number}\'e {order_count} sipariş başarıyla taşındı.'
                })
            
            # Normal form gönderimi için yönlendirme
            return redirect('pos:table_list')
            
        except Table.DoesNotExist:
            message = 'Masa bulunamadı.'
            if is_ajax:
                return JsonResponse({'status': 'error', 'message': message})
            return redirect('pos:table_list')
            
        except Exception as e:
            message = str(e)
            if is_ajax:
                return JsonResponse({'status': 'error', 'message': message})
            return redirect('pos:table_list')
    
    tables = Table.objects.all()
    return render(request, 'pos/table_transfer.html', {'tables': tables})

@login_required
def table_management(request):
    # Kullanıcının tenant'ını bul
    tenant = None
    try:
        tenant = request.user.owned_tenant
    except:
        tenant_membership = request.user.tenant_memberships.first()
        if tenant_membership:
            tenant = tenant_membership.tenant
    
    if not tenant:
        messages.error(request, 'Herhangi bir işletmeye bağlı değilsiniz. Lütfen sistem yöneticisi ile iletişime geçin.')
        return redirect('pos:index')
        
    tables = Table.objects.filter(tenant=tenant).order_by('floor', 'number')
    return render(request, 'pos/table_management.html', {'tables': tables})

@login_required
def table_open(request, table_id):
    if request.method == 'POST':
        try:
            table = get_object_or_404(Table, id=table_id)
            table.is_occupied = True
            table.save()
            return redirect('pos:table_detail', table_id=table.id)
        except Exception as e:
            return redirect('pos:table_detail', table_id=table_id)
    return redirect('pos:table_detail', table_id=table_id)

@login_required
def takeaway_orders(request):
    """Paket siparişler görünümü"""
    # Paket siparişleri getir
    orders_list = Order.objects.filter(order_type='takeaway').order_by('-created_at')
    
    # Sayfalama işlemi
    paginator = Paginator(orders_list, 10)  # Her sayfada 15 sipariş
    page = request.GET.get('page', 1)
    
    try:
        orders = paginator.page(page)
    except PageNotAnInteger:
        # Sayfa numarası bir tamsayı değilse, ilk sayfayı göster
        orders = paginator.page(1)
    except EmptyPage:
        # Sayfa numarası çok büyükse, son sayfayı göster
        orders = paginator.page(paginator.num_pages)

    context = {
        'orders': orders,
        'status_choices': Order.STATUS_CHOICES,
    }
    return render(request, 'pos/takeaway_orders.html', context)

@login_required
def order_cancel(request, order_id):
    if request.method == 'POST':
        try:
            order = get_object_or_404(Order, id=order_id)
            order.status = 'cancelled'
            order.save()
            
            # Eğer masa siparişi ise ve masada başka aktif sipariş yoksa masayı boşalt
            if order.table:
                active_orders = Order.objects.filter(
                    table=order.table,
                    status__in=['pending', 'preparing']
                ).exclude(id=order.id).exists()
                
                if not active_orders:
                    order.table.is_occupied = False
                    order.table.save()
                
                # Masa siparişi ise masalar sayfasına yönlendir
                return redirect('pos:table_list')
            
            # Paket sipariş ise siparişler sayfasına yönlendir
            return redirect('pos:order_list')
            
        except Exception as e:
            return redirect('pos:order_list')
    
    return redirect('pos:order_list')





