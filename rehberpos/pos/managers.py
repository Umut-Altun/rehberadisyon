from django.db import models
from django.apps import apps

class TenantQuerySet(models.QuerySet):
    """
    QuerySet that automatically filters by tenant.
    """
    def filter_by_tenant(self):
        """Filter queryset by the current tenant."""
        # Avoid circular import
        from .middleware import get_current_tenant
        
        tenant = get_current_tenant()
        
        # No tenant means either admin or unauthenticated request
        if tenant is None:
            return self
        
        # Check if the model supports tenant filtering
        if hasattr(self.model, 'tenant'):
            return self.filter(tenant=tenant)
        
        return self

class TenantManager(models.Manager):
    """
    Manager that returns a TenantQuerySet and automatically filters by tenant.
    """
    def get_queryset(self):
        return TenantQuerySet(self.model, using=self._db).filter_by_tenant() 