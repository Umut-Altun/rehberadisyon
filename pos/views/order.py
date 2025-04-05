from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.http import JsonResponse
from django.core.paginator import Paginator
from ..models import Order, OrderItem, Product, Table, Category, Customer

@login_required
def order_list(request):
    status = request.GET.get('status')
    date = request.GET.get('date')
    order_type = request.GET.get('order_type')
    page = request.GET.get('page', 1)
    
    orders = Order.objects.all().select_related('customer', 'table').prefetch_related('items')
    
    if status:
        orders = orders.filter(status=status)
    if date:
        orders = orders.filter(created_at__date=date)
    if order_type:
        orders = orders.filter(order_type=order_type)
    
    orders = orders.order_by('-created_at')
    
    paginator = Paginator(orders, 10)
    try:
        orders = paginator.page(page)
    except:
        orders = paginator.page(1)
    
    context = {
        'orders': orders,
        'status_choices': Order.STATUS_CHOICES,
        'order_type_choices': Order.ORDER_TYPE_CHOICES,
    }
    return render(request, 'pos/order_list.html', context)

@login_required
def order_create(request):
    if request.method == 'POST':
        order_type = request.POST.get('order_type', 'table')
        table_id = request.GET.get('table')
        customer_id = request.POST.get('customer') if order_type == 'takeaway' else None
        products = request.POST.getlist('products[]')
        quantities = request.POST.getlist('quantities[]')
        notes = request.POST.getlist('notes[]')
        
        try:
            with transaction.atomic():
                if order_type == 'table' and table_id:
                    existing_order = Order.objects.filter(
                        table_id=table_id,
                        status__in=['pending', 'preparing']
                    ).first()
                    
                    if existing_order:
                        order = existing_order
                    else:
                        order = Order.objects.create(
                            customer_id=customer_id,
                            table_id=table_id,
                            order_type=order_type,
                            status='pending',
                            staff=request.user
                        )
                else:
                    order = Order.objects.create(
                        customer_id=customer_id,
                        table_id=table_id if order_type == 'table' else None,
                        order_type=order_type,
                        status='pending',
                        staff=request.user
                    )
                
                total_amount = order.total_amount or 0
                for i in range(len(products)):
                    product = Product.objects.get(id=products[i])
                    quantity = int(quantities[i])
                    note = notes[i] if i < len(notes) else ''
                    
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=quantity,
                        unit_price=product.price,
                        notes=note
                    )
                    total_amount += product.price * quantity
                
                order.total_amount = total_amount
                order.save()
                
                if order.table:
                    order.table.is_occupied = True
                    order.table.save()
                    return redirect('pos:table_list')
                
                return redirect('pos:order_list')
            
        except Exception as e:
            if order_type == 'table':
                return redirect('pos:table_list')
            return redirect('pos:order_list')
    
    order_type = request.GET.get('type', 'table')
    table_id = request.GET.get('table')
    initial_customer_id = int(request.GET.get('customer')) if request.GET.get('customer') and order_type == 'takeaway' else None
    
    context = {
        'categories': Category.objects.all(),
        'products_by_category': {
            category: Product.objects.filter(category=category, is_available=True)
            for category in Category.objects.all()
        },
        'initial_customer_id': initial_customer_id,
        'order_type': order_type,
        'table_id': table_id,
    }
    
    if order_type == 'takeaway':
        context['customers'] = Customer.objects.all()
    
    return render(request, 'pos/order_create.html', context)

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order.objects.select_related('customer', 'table')
                             .prefetch_related('items__product'), id=order_id)
    total_items = order.items.aggregate(total=Sum('quantity'))['total'] or 0
    context = {
        'order': order,
        'total_items': total_items,
    }
    return render(request, 'pos/order_detail.html', context)

@login_required
def order_status_update(request, order_id):
    if request.method == 'POST':
        order = get_object_or_404(Order, id=order_id)
        new_status = request.POST.get('status')
        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status
            order.save()
            
            if new_status == 'completed' and order.table:
                order.table.is_occupied = False
                order.table.save()
            
            return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'})

@login_required
def order_delete(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if request.method == 'POST':
        if order.table:
            order.table.is_occupied = False
            order.table.save()
        order.delete()
        return redirect('pos:order_list')
    return render(request, 'pos/order_confirm_delete.html', {'order': order})

@login_required
def order_item_delete(request):
    """Sipariş ürünü silme view'ı"""
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        try:
            with transaction.atomic():
                # Ürünü bul ve sil
                order_item = get_object_or_404(OrderItem, id=item_id)
                order = order_item.order
                
                # Ürünün toplam tutarını hesapla
                item_total = order_item.quantity * order_item.unit_price
                
                # Ürünü sil
                order_item.delete()
                
                # Siparişin toplam tutarını güncelle
                order.total_amount = order.total_amount - item_total
                order.save()
                
                # Eğer siparişte hiç ürün kalmadıysa siparişi iptal et
                if not order.items.exists():
                    order.status = 'cancelled'
                    order.save()
                    
                    # Eğer masa siparişi ise ve başka aktif sipariş yoksa masayı boşalt
                    if order.table:
                        active_orders = Order.objects.filter(
                            table=order.table,
                            status__in=['pending', 'preparing']
                        ).exclude(id=order.id)
                        
                        if not active_orders.exists():
                            order.table.is_occupied = False
                            order.table.save()
                
                return JsonResponse({'success': True})
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
            
    return JsonResponse({
        'success': False,
        'error': 'Geçersiz istek metodu'
    })

@login_required
def kitchen_display(request):
    """Mutfak ekranı görünümü"""
    # Aktif siparişleri al (bekleyen ve hazırlanan)
    active_orders = Order.objects.filter(
        status__in=['pending', 'preparing']
    ).select_related(
        'table', 'customer'
    ).prefetch_related(
        'items__product'
    ).order_by(
        'created_at'  # En eski siparişler önce
    )
    
    context = {
        'active_orders': active_orders
    }
    return render(request, 'pos/kitchen_display.html', context)
