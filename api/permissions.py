# api/permissions.py
from rest_framework import permissions

class EsSuperAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.rol == 'super_admin')

class EsAdminCliente(permissions.BasePermission):
    def has_permission(self, request, view):
        # CORRECCIÓN: Ahora el super_admin también cuenta como admin_cliente
        return bool(request.user and request.user.is_authenticated and request.user.rol in ['admin_cliente', 'super_admin'])

class EsGerente(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.rol in ['gerente', 'super_admin'])

class EsVendedor(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.rol in ['vendedor', 'super_admin'])

# Permisos combinados
class EsAdminOGerente(permissions.BasePermission):
    def has_permission(self, request, view):
        usuario = request.user
        # CORRECCIÓN: Agregamos super_admin a la lista
        return bool(usuario and usuario.is_authenticated and usuario.rol in ['admin_cliente', 'gerente', 'super_admin'])

class EsAdminOVendedor(permissions.BasePermission):
    def has_permission(self, request, view):
        usuario = request.user
        # CORRECCIÓN: Agregamos 'gerente' a la lista para que pueda ver los reportes de ventas
        return bool(usuario and usuario.is_authenticated and usuario.rol in ['admin_cliente', 'vendedor', 'super_admin', 'gerente'])

# Permiso para que usuarios vean/modifiquen solo sus datos
class EsPropietarioOAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # Super admin puede todo (Esto ya estaba bien, pero lo mantenemos)
        if request.user.rol == 'super_admin':
            return True
        
        # Si el objeto es el usuario mismo
        if obj == request.user:
            return True
        
        # Si el objeto tiene usuario, verificar si es el dueño
        if hasattr(obj, 'usuario'):
            return obj.usuario == request.user
        
        # Si el objeto tiene vendedor, verificar si es el vendedor
        if hasattr(obj, 'vendedor'):
            return obj.vendedor == request.user
        
        # Admin cliente puede modificar objetos de su compañía
        if request.user.rol == 'admin_cliente' and hasattr(obj, 'compania'):
            return obj.compania == request.user.compania
        
        return False

# Permiso para lectura/escritura según rol
class SoloLecturaParaVendedor(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.rol in ['super_admin', 'admin_cliente', 'gerente']