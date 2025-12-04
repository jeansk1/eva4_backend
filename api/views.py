# api/views.py - VERSIÓN FINAL Y CORREGIDA
from rest_framework import viewsets, generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.db.models import F, Sum, Count, Q # Importante para reportes y filtros
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .serializers import *
from .permissions import *
from core.models import *

Usuario = get_user_model()

# --- Vistas de Usuario ---
class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    
    # PERMISOS DINÁMICOS:
    # - Para crear usuarios: Solo Admins
    # - Para listar usuarios: Solo Admins
    # - Para ver/editar: El propio usuario O un Admin
    def get_permissions(self):
        if self.action in ['create', 'list', 'destroy']:
            return [IsAuthenticated(), EsAdminOGerente()] # O EsSuperAdmin si prefieres
        
        # Para retrieve (ver detalle) o update/partial_update (editar perfil/pass)
        # Permitimos si es el dueño de la cuenta
        return [IsAuthenticated()] 

    def get_queryset(self):
        usuario = self.request.user
        if usuario.rol == 'super_admin':
            return Usuario.objects.all()
        # Admin Cliente ve a los de su empresa
        if usuario.rol == 'admin_cliente':
            return Usuario.objects.filter(compania=usuario.compania)
        # Usuario normal solo se ve a sí mismo (para evitar que un vendedor vea a otros por ID)
        return Usuario.objects.filter(id=usuario.id)

class UsuarioActualView(APIView):
    # Esto permite que CUALQUIER usuario logueado (vendedor, gerente) vea su perfil
    permission_classes = [IsAuthenticated] 
    
    def get(self, request):
        serializer = UsuarioSerializer(request.user)
        return Response(serializer.data)

# --- Vistas Estructurales ---
class CompaniaViewSet(viewsets.ModelViewSet):
    queryset = Compania.objects.all()
    serializer_class = CompaniaSerializer
    permission_classes = [IsAuthenticated, EsSuperAdmin]

class SucursalViewSet(viewsets.ModelViewSet):
    queryset = Sucursal.objects.all()
    serializer_class = SucursalSerializer
    # ELIMINAMOS la clase permission_classes estricta de aquí.
    
    def get_queryset(self):
        usuario = self.request.user
        if usuario.rol == 'super_admin':
            return Sucursal.objects.all()
        # Filtra solo sucursales de la compañía del usuario
        return Sucursal.objects.filter(compania=usuario.compania)

    def get_permissions(self):
        # ESTA ES LA CLAVE: Permitimos que CUALQUIER usuario logueado (incluido el Cajero)
        # pueda ver la lista de sucursales (acciones 'list' y 'retrieve').
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()] 
        
        # Para crear/editar/borrar, mantenemos la restricción de AdminCliente.
        return [IsAuthenticated(), EsAdminCliente()]

# --- Vistas de Producto e Inventario ---
class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer
    
    # Por defecto protegemos todo, pero get_permissions hace la excepción
    permission_classes = [IsAuthenticated, EsAdminOGerente]
    
    def get_queryset(self):
        usuario = self.request.user
        
        # 1. Si es usuario anónimo (tienda pública), mostramos todo
        if not usuario.is_authenticated:
            return Producto.objects.all()

        # 2. Si es Super Admin, ve todo.
        if usuario.rol == 'super_admin':
            return Producto.objects.all()
        
        # 3. FILTRO CORREGIDO (Clave): Vendedores y otros roles ven productos de SU compañía,
        #    PERO solo si la tienen asignada.
        if usuario.compania:
            return Producto.objects.filter(compania=usuario.compania)
        
        # 4. Si es empleado pero NO tiene compañía asignada, devuelve una lista vacía.
        return Producto.objects.none()
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            # Permitimos que Vendedores y público VEAN los productos
            return [AllowAny()] 
        return [IsAuthenticated(), EsAdminOGerente()] # Para editar/crear/borrar

class InventarioViewSet(viewsets.ModelViewSet):
    queryset = Inventario.objects.all()
    serializer_class = InventarioSerializer
    # Quitamos la clase estricta y delegamos a get_permissions
    permission_classes = [IsAuthenticated, EsAdminOGerente] 
    
    def get_queryset(self):
        usuario = self.request.user
        queryset = Inventario.objects.all()
        
        if usuario.is_authenticated and usuario.rol != 'super_admin':
            queryset = queryset.filter(sucursal__compania=usuario.compania)
        
        sucursal_id = self.request.query_params.get('sucursal', None)
        if sucursal_id:
            queryset = queryset.filter(sucursal_id=sucursal_id)
        
        return queryset

    # 👇 ESTE MÉTODO ES LA CLAVE PARA EL CAJERO 👇
    def get_permissions(self):
        # Permitimos que CUALQUIER usuario logueado VEA los datos de inventario.
        if self.action in ['list', 'retrieve']:
            return [AllowAny()] 
        
        # Para modificar el stock (create, update, destroy), solo Administradores o Gerentes.
        return [IsAuthenticated(), EsAdminOGerente()]

class ProveedorViewSet(viewsets.ModelViewSet):
    queryset = Proveedor.objects.all()
    serializer_class = ProveedorSerializer
    permission_classes = [IsAuthenticated, EsAdminOGerente]
    
    def get_queryset(self):
        usuario = self.request.user
        if usuario.rol == 'super_admin':
            return Proveedor.objects.all()
        return Proveedor.objects.filter(compania=usuario.compania)

# --- Vista de COMPRAS (NUEVA - Requisito Obligatorio) ---
class CompraViewSet(viewsets.ModelViewSet):
    queryset = Compra.objects.all()
    serializer_class = CompraSerializer
    permission_classes = [IsAuthenticated, EsAdminOGerente]
    
    def get_queryset(self):
        usuario = self.request.user
        if usuario.rol == 'super_admin':
            return Compra.objects.all()
        return Compra.objects.filter(sucursal__compania=usuario.compania)

# --- Vistas de Ventas y Órdenes ---
class VentaViewSet(viewsets.ModelViewSet):
    queryset = Venta.objects.all()
    permission_classes = [IsAuthenticated, EsAdminOVendedor]
    
    def get_serializer_class(self):
        # Usar serializer detallado para crear (maneja stock), simple para listar
        if self.action in ['create', 'update', 'retrieve']:
            return VentaConItemsSerializer
        return VentaSerializer
    
    def get_queryset(self):
        usuario = self.request.user
        queryset = Venta.objects.select_related('sucursal', 'vendedor').all()
        
        if usuario.rol == 'vendedor':
            queryset = queryset.filter(vendedor=usuario)
        elif usuario.rol in ['admin_cliente', 'gerente']:
            queryset = queryset.filter(sucursal__compania=usuario.compania)
        
        # Filtros para reportes
        sucursal_id = self.request.query_params.get('sucursal', None)
        fecha_desde = self.request.query_params.get('fecha_desde', None)
        fecha_hasta = self.request.query_params.get('fecha_hasta', None)
        
        if sucursal_id:
            queryset = queryset.filter(sucursal_id=sucursal_id)
        if fecha_desde:
            queryset = queryset.filter(creado_en__date__gte=fecha_desde)
        if fecha_hasta:
            queryset = queryset.filter(creado_en__date__lte=fecha_hasta)
        
        return queryset
    
    def perform_create(self, serializer):
        # Asignar automáticamente el vendedor actual
        serializer.save(vendedor=self.request.user)

class OrdenViewSet(viewsets.ModelViewSet):
    queryset = Orden.objects.all()
    serializer_class = OrdenSerializer
    permission_classes = [AllowAny] 
    
    def get_queryset(self):
        # Evitar error en generación de esquemas
        if getattr(self, 'swagger_fake_view', False):
            return Orden.objects.none()

        user = self.request.user
        queryset = Orden.objects.all() # Base

        # 1. Filtro de Seguridad (Quién ve qué)
        if user.is_authenticated:
            if user.rol != 'super_admin' and user.rol in ['admin_cliente', 'gerente']:
                # Ver órdenes de mi empresa + órdenes nuevas sin asignar (web)
                queryset = queryset.filter(
                    Q(sucursal__compania=user.compania) | Q(sucursal__isnull=True)
                )
            # Si es vendedor, quizás no debería ver nada, o solo las suyas, 
            # pero aquí mantenemos la lógica abierta para el dashboard.
        
        # 2. Filtro Funcional (Por estado) - ¡ESTO FALTABA!
        estado = self.request.query_params.get('estado')
        if estado:
            queryset = queryset.filter(estado=estado)
            
        return queryset

    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        if self.action in ['list', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated()]
        return [AllowAny()]

    def perform_create(self, serializer):
        # Asignar a la primera sucursal para que no quede huérfana
        primera_sucursal = Sucursal.objects.first()
        serializer.save(sucursal=primera_sucursal)

class ItemCarritoViewSet(viewsets.ModelViewSet):
    queryset = ItemCarrito.objects.all()
    serializer_class = ItemCarritoSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return ItemCarrito.objects.filter(usuario=self.request.user)
    
    def perform_create(self, serializer):
        producto_id = self.request.data.get('producto')
        cantidad = int(self.request.data.get('cantidad', 1))
        
        producto = get_object_or_404(Producto, id=producto_id)
        
        # Lógica de "Agregar o Incrementar"
        item_carrito, creado = ItemCarrito.objects.get_or_create(
            usuario=self.request.user,
            producto=producto,
            defaults={'cantidad': 0}
        )
        
        # Si ya existía o se acaba de crear, sumamos la cantidad
        item_carrito.cantidad += cantidad
        item_carrito.save()

# --- Vistas de Reporte (CORREGIDA CON F()) ---
class ReporteView(APIView):
    permission_classes = [IsAuthenticated, EsAdminOGerente]
    
    def get(self, request):
        tipo_reporte = request.query_params.get('tipo', 'stock')
        usuario = request.user
        
        if tipo_reporte == 'stock':
            # Reporte de stock por sucursal
            sucursales = Sucursal.objects.filter(compania=usuario.compania)
            datos = []
            for sucursal in sucursales:
                inventario = Inventario.objects.filter(sucursal=sucursal)
                datos.append({
                    'sucursal': sucursal.nombre,
                    'total_productos': inventario.count(),
                    # F() permite comparar columna contra columna en la DB
                    'bajo_stock': inventario.filter(stock__lte=F('punto_reorden')).count(),
                    'agotado': inventario.filter(stock=0).count(),
                })
            return Response({'reporte_stock': datos})
        
        elif tipo_reporte == 'ventas':
            # Reporte de ventas con agregación (Sum)
            fecha_desde = request.query_params.get('fecha_desde')
            fecha_hasta = request.query_params.get('fecha_hasta')
            
            ventas = Venta.objects.filter(sucursal__compania=usuario.compania)
            
            if fecha_desde:
                ventas = ventas.filter(creado_en__date__gte=fecha_desde)
            if fecha_hasta:
                ventas = ventas.filter(creado_en__date__lte=fecha_hasta)
            
            # Calcular totales directamente en la base de datos
            resumen = ventas.aggregate(
                total_cantidad=Count('id'),
                total_monto=Sum('total')
            )
            
            return Response({
                'total_ventas': resumen['total_cantidad'],
                'total_monto': resumen['total_monto'] or 0,
                'periodo': f'{fecha_desde} a {fecha_hasta}' if fecha_desde and fecha_hasta else 'Historico'
            })
        
        return Response({'error': 'Tipo de reporte inválido'}, status=400)

# --- Vistas de Utilidad y Auth ---
class VistaPruebaAPI(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        return Response({
            'mensaje': 'API funcionando correctamente',
            'usuario': request.user.username,
            'rol': request.user.rol,
            'compania': request.user.compania.nombre if request.user.compania else None
        })

#--- Vistas de Autenticación JWT Personalizada ---
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Serializador modificado para inyectar el rol y el plan de suscripción 
    de la compañía en la respuesta JWT.
    """
    def validate(self, attrs):
        data = super().validate(attrs)
        
        plan_name = 'Básico' # Valor por defecto si no hay plan explícito
        
        # Intentamos obtener el plan de suscripción
        if self.user.compania:
            try:
                # Asumiendo que Compania tiene un campo Suscripcion (ej: a través de un OneToOneField)
                if hasattr(self.user.compania, 'suscripcion') and self.user.compania.suscripcion:
                    plan_name = self.user.compania.suscripcion.plan
            except Suscripcion.DoesNotExist:
                # Si la compañía existe pero no tiene suscripción (queda como Básico)
                plan_name = 'Básico'
            except AttributeError:
                # Evita fallos si la relación suscripcion no está definida
                pass

        # Agregar datos extra al response del login
        data.update({
            'username': self.user.username,
            'email': self.user.email,
            'rol': self.user.rol,
            'compania_id': self.user.compania.id if self.user.compania else None,
            'compania_nombre': self.user.compania.nombre if self.user.compania else None,
            # 👇 NUEVO CAMPO CLAVE QUE EL FRONTEND USARÁ PARA RESTRINGIR
            'plan': plan_name,  
        })
        return data

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer