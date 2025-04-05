from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from ..models import Category
from ..forms import CategoryForm
from django.contrib import messages
from django.http import HttpResponseForbidden

@login_required
def category_list(request):
    # Tenant kontrolü
    tenant = getattr(request, 'tenant', None)
    if not tenant:
        messages.error(request, "İşletme bilgisi bulunamadı.")
        return redirect('pos:index')
    
    categories = Category.objects.filter(tenant=tenant).order_by('name')
    return render(request, 'pos/category_list.html', {'categories': categories})

@login_required
def category_create(request):
    # Tenant kontrolü
    tenant = getattr(request, 'tenant', None)
    if not tenant:
        messages.error(request, "İşletme bilgisi bulunamadı.")
        return redirect('pos:index')
    
    if request.method == 'POST':
        form = CategoryForm(request.POST, tenant=tenant)
        if form.is_valid():
            form.save()
            messages.success(request, "Kategori başarıyla oluşturuldu.")
            return redirect('pos:category_list')
    else:
        form = CategoryForm(tenant=tenant)
    
    return render(request, 'pos/category_create.html', {'form': form})

@login_required
def category_edit(request, category_id):
    # Tenant kontrolü
    tenant = getattr(request, 'tenant', None)
    if not tenant:
        messages.error(request, "İşletme bilgisi bulunamadı.")
        return redirect('pos:index')
    
    # Kategori tenant kontrolü
    category = get_object_or_404(Category, id=category_id)
    if category.tenant != tenant:
        messages.error(request, "Bu kategoriye erişim izniniz bulunmuyor.")
        return redirect('pos:category_list')
    
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category, tenant=tenant)
        if form.is_valid():
            form.save()
            messages.success(request, "Kategori başarıyla güncellendi.")
            return redirect('pos:category_list')
    else:
        form = CategoryForm(instance=category, tenant=tenant)
    
    return render(request, 'pos/category_edit.html', {'form': form, 'category': category})

@login_required
def category_delete(request, category_id):
    # Tenant kontrolü
    tenant = getattr(request, 'tenant', None)
    if not tenant:
        messages.error(request, "İşletme bilgisi bulunamadı.")
        return redirect('pos:index')
    
    # Kategori tenant kontrolü
    category = get_object_or_404(Category, id=category_id)
    if category.tenant != tenant:
        messages.error(request, "Bu kategoriye erişim izniniz bulunmuyor.")
        return redirect('pos:category_list')
    
    if request.method == 'POST':
        try:
            category.delete()
            messages.success(request, "Kategori başarıyla silindi.")
            return redirect('pos:category_list')
        except Exception as e:
            messages.error(request, f"Kategori silinemedi: {str(e)}")
            return redirect('pos:category_list')
    
    return render(request, 'pos/category_confirm_delete.html', {'category': category}) 