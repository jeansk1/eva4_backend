# api/permissions.py
from rest_framework import permissions
from core.models import Suscripcion

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
    
class PermisoPlanEstandar(permissions.BasePermission):
    """Permite el acceso solo si el plan es Estándar o Premium."""
    message = 'Se requiere el Plan Estándar o superior para acceder a esta funcionalidad (Reportes/Valoración).'

    def has_permission(self, request, view):
        # El SuperAdmin siempre puede
        if request.user.rol == 'super_admin':
            return True

        compania = request.user.compania
        if not compania:
            return False

        try:
            # Buscar la suscripción activa
            suscripcion = compania.suscripcion
            plan_actual = suscripcion.plan
            
            # Requisitos para Plan Estándar (o Premium)
            return plan_actual in ['estandar', 'premium'] and suscripcion.activo
        except Suscripcion.DoesNotExist:
            # Si no tiene suscripción, por defecto queda en 'basico' (no tiene acceso a estandar/premium)
            return False

class PermisoPlanPremium(permissions.BasePermission):
    """Permite el acceso solo si el plan es Premium (e-commerce)."""
    message = 'Se requiere el Plan Premium para acceder a esta funcionalidad (Tienda Online/Órdenes).'

    def has_permission(self, request, view):
        print(f"\n🔍 DEBUG PermisoPlanPremium - URL: {request.path}")
        print(f"  Usuario: {request.user.username if request.user.is_authenticated else 'Anónimo'}")
        print(f"  Rol: {request.user.rol if request.user.is_authenticated else 'N/A'}")
        
        # El SuperAdmin siempre puede
        if request.user.rol == 'super_admin':
            print("  ✅ SuperAdmin - Acceso permitido")
            return True

        if not request.user.is_authenticated:
            print("  ❌ Usuario no autenticado")
            return False

        compania = request.user.compania
        print(f"  Compañía: {compania.nombre if compania else 'N/A'}")
        
        if not compania:
            print("  ❌ Usuario sin compañía")
            return False

        try:
            # Buscar la suscripción activa
            suscripcion = compania.suscripcion
            print(f"  Plan en BD: {suscripcion.plan}")
            print(f"  Suscripción activa: {suscripcion.activo}")
            print(f"  Fecha término: {suscripcion.fecha_termino}")
            
            # Verificar si la suscripción está activa
            from django.utils import timezone
            hoy = timezone.now().date()
            print(f"  Hoy: {hoy}")
            
            # Requisitos para Plan Premium
            if suscripcion.plan == 'premium' and suscripcion.activo and suscripcion.fecha_termino >= hoy:
                print("  ✅ Plan Premium activo - Acceso permitido")
                return True
            else:
                print(f"  ❌ Plan no es Premium o inactivo/vencido: {suscripcion.plan}")
                return False
                
        except Suscripcion.DoesNotExist:
            print("  ❌ No existe suscripción para esta compañía")
            return False
        except Exception as e:
            print(f"  ❌ Error inesperado: {e}")
            import traceback
            traceback.print_exc()
            return False
        
class PermisoLimiteSucursales(permissions.BasePermission):
    """Verifica que no se exceda el límite de sucursales según el plan."""
    message = 'Has alcanzado el límite de sucursales permitido por tu plan.'

    def has_permission(self, request, view):
        # Solo aplicar para creación de sucursales
        if request.method != 'POST':
            return True

        # SuperAdmin siempre puede
        if request.user.rol == 'super_admin':
            return True

        compania = request.user.compania
        if not compania:
            return False

        try:
            suscripcion = compania.suscripcion
            max_permitido = suscripcion.max_sucursales
            
            # Contar sucursales actuales
            from core.models import Sucursal
            sucursales_actuales = Sucursal.objects.filter(compania=compania).count()
            
            return sucursales_actuales < max_permitido
            
        except Suscripcion.DoesNotExist:
            # Sin suscripción = plan básico = 1 sucursal
            from core.models import Sucursal
            sucursales_actuales = Sucursal.objects.filter(compania=compania).count()
            return sucursales_actuales < 1