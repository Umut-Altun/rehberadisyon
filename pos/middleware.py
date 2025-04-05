from django.utils.deprecation import MiddlewareMixin
from django.db.models.signals import pre_save
from django.dispatch import receiver
import threading
from .models import Tenant

# Thread-local storage to store the current tenant
_thread_local = threading.local()

def get_current_tenant():
    """
    Returns the tenant associated with the current thread.
    """
    return getattr(_thread_local, 'tenant', None)

def set_current_tenant(tenant):
    """
    Sets the tenant for the current thread.
    """
    _thread_local.tenant = tenant

class TenantMiddleware(MiddlewareMixin):
    """
    Middleware that sets the tenant based on the logged-in user.
    """
    def process_request(self, request):
        # Clear the tenant at the start of a new request
        set_current_tenant(None)
        
        # Set tenant for authenticated users
        if request.user.is_authenticated:
            # Önce oturumdan tenant_id'yi kontrol et
            tenant_id = request.session.get('current_tenant_id')
            
            if tenant_id:
                try:
                    # ID'den tenant'ı bul
                    tenant = Tenant.objects.get(id=tenant_id)
                    set_current_tenant(tenant)
                    # Store tenant in request for easy access in views
                    request.tenant = tenant
                    
                    # Kullanıcı rolünü bir kez belirleyip session'a kaydet
                    # Böylece her sayfa yüklemesinde tekrar veritabanı sorgusu yapmamız gerekmez
                    if 'user_role' not in request.session:
                        from .models import TenantUser
                        # Önce tenant sahibi mi kontrol et
                        if tenant.owner_id == request.user.id:
                            request.session['user_role'] = 'owner'
                        else:
                            # TenantUser ilişkisini kontrol et
                            try:
                                tenant_user = TenantUser.objects.get(
                                    tenant=tenant,
                                    user=request.user,
                                    is_active=True
                                )
                                request.session['user_role'] = tenant_user.role
                            except TenantUser.DoesNotExist:
                                # Rol bulunamadıysa varsayılan rol
                                request.session['user_role'] = 'unknown'
                    
                    # Rol bilgisini request nesnesine de ekle
                    request.user_role = request.session.get('user_role')
                    
                    return None
                except Tenant.DoesNotExist:
                    # Geçersiz tenant_id ise session'dan kaldır
                    if 'current_tenant_id' in request.session:
                        del request.session['current_tenant_id']
                    if 'user_role' in request.session:
                        del request.session['user_role']
            
            # Session'da tenant_id yoksa kullanıcının işletme sahibi olduğu tenant'ı kontrol et
            try:
                tenant = getattr(request.user, 'owned_tenant', None)
                if tenant:
                    set_current_tenant(tenant)
                    # Store tenant in request for easy access in views
                    request.tenant = tenant
                    # Tenant ID'yi ve rolü session'a ekle
                    request.session['current_tenant_id'] = tenant.id
                    request.session['user_role'] = 'owner'
                    request.user_role = 'owner'
                else:
                    # Kullanıcı bir tenant'a ait olabilir, TenantUser tablosunu kontrol et
                    from .models import TenantUser
                    try:
                        tenant_user = TenantUser.objects.filter(user=request.user, is_active=True).first()
                        if tenant_user:
                            tenant = tenant_user.tenant
                            set_current_tenant(tenant)
                            request.tenant = tenant
                            request.session['current_tenant_id'] = tenant.id
                            request.session['user_role'] = tenant_user.role
                            request.user_role = tenant_user.role
                    except Exception as e:
                        print(f"DEBUG - TenantMiddleware: Error checking TenantUser: {str(e)}")
            except Exception as e:
                print(f"DEBUG - TenantMiddleware: Error getting owned_tenant: {str(e)}")
        
        return None

@receiver(pre_save)
def tenant_pre_save_handler(sender, instance, **kwargs):
    """
    Signal handler to automatically set the tenant for new objects.
    """
    # Skip if this is not a tenant-enabled model
    if not hasattr(instance, 'tenant_id'):
        return
    
    # Skip if tenant is already set or if we have no current tenant
    if instance.tenant_id is not None or get_current_tenant() is None:
        return
    
    # Set the tenant if it's not already set
    instance.tenant = get_current_tenant() 