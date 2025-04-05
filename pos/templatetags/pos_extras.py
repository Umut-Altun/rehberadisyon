from django import template
from ..models import TenantUser

register = template.Library()

@register.filter
def multiply(value, arg):
    """İki sayıyı çarpar"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def get_item(dictionary, key):
    """Sözlükten belirtilen anahtarla değer alır"""
    return dictionary.get(key)

@register.filter
def has_role(user, roles):
    """
    Kullanıcının belirli bir rolü olup olmadığını kontrol eder
    Örnek kullanım: {% if user|has_role:"owner,manager" %}
    """
    if not user or not user.is_authenticated:
        return False
    
    # Süper kullanıcılar her şeyi görebilir
    if user.is_superuser:
        return True
    
    # Virgülle ayrılmış rolleri listeye çevir
    role_list = [r.strip() for r in roles.split(',')]
    
    # Mevcut tenant'ı session'dan al
    request = getattr(user, 'request', None)
    current_tenant_id = None
    
    if request:
        current_tenant_id = request.session.get('current_tenant_id')
    else:
        print(f"DEBUG - has_role: {user.username} has no request object")
    
    if current_tenant_id:
        try:
            # Kullanıcının tenant ile ilişkisini bul
            tenant_user = TenantUser.objects.get(
                user=user,
                tenant_id=current_tenant_id,
                is_active=True
            )
            # Kullanıcının rolü listemizde var mı?
            has_role = tenant_user.role in role_list
            return has_role
        except TenantUser.DoesNotExist:
            # İşletme sahibi mi kontrol et
            from ..models import Tenant
            try:
                tenant = Tenant.objects.get(id=current_tenant_id)
                is_owner = tenant.owner_id == user.id
                has_role = 'owner' in role_list and is_owner
                print(f"DEBUG - has_role: {user.username} is tenant owner={is_owner}, checking against {role_list}, result={has_role}")
                return has_role
            except Tenant.DoesNotExist:
                pass
    else:
        print(f"DEBUG - has_role: No current_tenant_id for {user.username}")
            
    print(f"DEBUG - has_role: {user.username} default returning False")
    return False 