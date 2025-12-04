# api/views.py -
from rest_framework import viewsets, generics, status, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.db.models import F, Sum, Count, Q
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

# Importa todos los serializers desde api/serializers.py
from .serializers import *

# Importa todos los permisos desde api/permissions.py
from .permissions import *

# Importa todos los modelos desde core/models.py
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
    
    # 👇 NUEVO: ENDPOINT PARA QUE EL SUPER_ADMIN ACTIVE UNA SUSCRIPCIÓN
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, EsSuperAdmin])
    def subscribe(self, request, pk=None):
        """Activa o actualiza la suscripción de una compañía (solo Super Admin)."""
        compania = get_object_or_404(Compania, pk=pk)
        
        # Usamos SuscripcionSerializer para validar los datos de entrada
        serializer = SuscripcionSerializer(data=request.data) 
        
        if serializer.is_valid():
            data = serializer.validated_data
            
            # Actualizar o crear la suscripción de la compañía
            Suscripcion.objects.update_or_create(
                compania=compania,
                defaults={
                    'plan': data.get('plan'),
                    'fecha_inicio': data.get('fecha_inicio'),
                    'fecha_termino': data.get('fecha_termino'),
                    'activo': data.get('activo', True),
                    # Es crucial enviar o calcular 'max_sucursales' aquí
                    'max_sucursales': data.get('max_sucursales', 1) 
                }
            )
            return Response({'status': f'Suscripción de {compania.nombre} actualizada a {data.get("plan").upper()} correctamente.'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SucursalViewSet(viewsets.ModelViewSet):
    queryset = Sucursal.objects.all()
    serializer_class = SucursalSerializer
    
    def get_queryset(self):
        usuario = self.request.user
        if usuario.rol == 'super_admin':
            return Sucursal.objects.all()
        # Filtra solo sucursales de la compañía del usuario
        return Sucursal.objects.filter(compania=usuario.compania)

    def get_permissions(self):
        # ✅ MODIFICACIÓN: Agregar PermisoLimiteSucursales para creación
        if self.action == 'create':
            return [IsAuthenticated(), EsAdminCliente(), PermisoLimiteSucursales()]
        
        # Para listar/ver, solo autenticación
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        
        # Para editar/borrar, admin cliente
        return [IsAuthenticated(), EsAdminCliente()]
    
    # 👇 NUEVO: RESTRICCIÓN DEL LÍMITE DE SUCURSALES POR PLAN
    def perform_create(self, serializer):
        user = self.request.user
        compania = user.compania
        
        # 1. Determinar límites del plan
        try:
            suscripcion = compania.suscripcion
            max_sucursales = suscripcion.max_sucursales
            plan_name = suscripcion.plan.upper()
        except Suscripcion.DoesNotExist:
            # Plan por defecto si no hay suscripción activa (Plan Básico)
            max_sucursales = 1 
            plan_name = 'BÁSICO'

        # 2. Contar sucursales existentes
        current_count = Sucursal.objects.filter(compania=compania).count()
        
        # 3. Validar el límite
        if current_count >= max_sucursales:
            raise serializers.ValidationError(
                {'error': f"Límite de sucursales excedido. Su plan ({plan_name}) solo permite {max_sucursales} sucursal(es)."}
            )

        # 4. Asignar y guardar si la validación pasa
        serializer.save(compania=compania)

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
        #    PERO solo si la tienen asignada.
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
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Orden.objects.none()

        user = self.request.user
        queryset = Orden.objects.all()

        print(f"\n🔍 DEBUG OrdenViewSet.get_queryset()")
        print(f"  Usuario: {user.username if user.is_authenticated else 'Anónimo'}")
        print(f"  Rol: {user.rol if user.is_authenticated else 'N/A'}")
        print(f"  Acción: {self.action}")

        # 1. Filtro de Seguridad
        if user.is_authenticated:
            print(f"  Compañía: {user.compania.nombre if user.compania else 'N/A'}")
            
            # SuperAdmin ve todo
            if user.rol == 'super_admin':
                print("  ✅ SuperAdmin - Sin filtros")
            # AdminCliente y Gerente ven órdenes de su compañía
            elif user.rol in ['admin_cliente', 'gerente']:
                print(f"  👥 Filtrando por compañía: {user.compania.nombre}")
                queryset = queryset.filter(
                    Q(sucursal__compania=user.compania) | Q(sucursal__isnull=True)
                )
            # Vendedor ve solo órdenes de su sucursal
            elif user.rol == 'vendedor' and user.compania:
                print("  🛒 Vendedor - Filtrando por sucursales de su compañía")
                sucursales_vendedor = Sucursal.objects.filter(compania=user.compania)
                queryset = queryset.filter(sucursal__in=sucursales_vendedor)
        
        # 2. Filtro por estado (si se solicita)
        estado = self.request.query_params.get('estado')
        if estado:
            print(f"  📊 Filtrando por estado: {estado}")
            queryset = queryset.filter(estado=estado)
            
        print(f"  📦 Total órdenes encontradas: {queryset.count()}")
        return queryset

    def get_permissions(self):
        print(f"\n🔍 DEBUG OrdenViewSet.get_permissions()")
        print(f"  Acción: {self.action}")
        
        # POST /api/ordenes/ (Checkout) - Abierto para todos (e-commerce público)
        if self.action == 'create':
            print("  ✅ Acción 'create' - Permitir a todos")
            return [AllowAny()]
        
        # GET /api/ordenes/ (Listar) - Requiere autenticación + Plan Premium
        if self.action == 'list':
            print("  📋 Acción 'list' - Verificando permisos...")
            
            # TEMPORAL: Descomenta la siguiente línea para test rápido
            # return [IsAuthenticated()]  # ← Descomentar para test rápido (permite ver sin plan premium)
            
            # Original con verificación de plan premium
            return [IsAuthenticated(), PermisoPlanPremium()]
        
        # PUT/PATCH/DELETE (Modificar) - Requiere Admin/Gerente + Plan Premium
        if self.action in ['update', 'partial_update', 'destroy', 'retrieve']:
            print(f"  ✏️ Acción '{self.action}' - Verificando permisos admin...")
            return [IsAuthenticated(), EsAdminOGerente(), PermisoPlanPremium()]
        
        # Por defecto (para otras acciones como OPTIONS)
        print("  🔧 Acción por defecto - AllowAny")
        return [AllowAny()]

class ItemCarritoViewSet(viewsets.ModelViewSet):
    """
    Vista para manejar el carrito de compras.
    FUNCIONA PARA USUARIOS AUTENTICADOS Y ANÓNIMOS.
    """
    queryset = ItemCarrito.objects.all()
    serializer_class = ItemCarritoSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        """
        Devuelve los items del carrito basados en:
        - Usuario autenticado: items de su usuario
        - Usuario anónimo: items de su sesión
        """
        # DEBUG información
        print(f"\n🎯 CARRITO - get_queryset()")
        print(f"  📍 URL: {self.request.path}")
        print(f"  🆔 Session Key: {self.request.session.session_key}")
        print(f"  👤 Usuario: {self.request.user}")
        print(f"  🔐 Autenticado: {self.request.user.is_authenticated}")
        
        # FORZAR creación de sesión si no existe (para anónimos)
        if not self.request.session.session_key:
            print("  ⚠️ No hay sesión - creando...")
            self.request.session.create()
            print(f"  ✅ Nueva sesión: {self.request.session.session_key}")
        
        session_key = self.request.session.session_key
        
        # Si el usuario está autenticado, mostrar sus items
        if self.request.user.is_authenticated:
            print(f"  👤 Buscando items del usuario: {self.request.user.username}")
            queryset = ItemCarrito.objects.filter(
                Q(usuario=self.request.user) | Q(clave_sesion=session_key)
            )
        else:
            # Usuario anónimo - buscar por session key
            print(f"  🎭 Usuario anónimo - buscando por session: {session_key}")
            queryset = ItemCarrito.objects.filter(clave_sesion=session_key)
        
        print(f"  📦 Items encontrados: {queryset.count()}")
        
        # DEBUG: Mostrar todos los items en DB
        all_items = ItemCarrito.objects.all()
        print(f"  🗄️ TOTAL items en DB: {all_items.count()}")
        for item in all_items:
            usuario_info = item.usuario.username if item.usuario else f"Anónimo({item.clave_sesion[:8] if item.clave_sesion else 'SinSesion'})"
            print(f"    - ID:{item.id} | Producto:{item.producto.nombre[:15] if item.producto else 'None'} | "
                  f"Usuario:{usuario_info} | Cantidad:{item.cantidad}")
        
        return queryset
    
    def perform_create(self, serializer):
        """
        Guarda el item del carrito automáticamente asignando:
        - usuario (si está autenticado)
        - clave_sesion (si es anónimo)
        """
        print(f"\n🎯 CARRITO - perform_create()")
        print(f"  📦 Datos recibidos: {self.request.data}")
        print(f"  🆔 Session Key: {self.request.session.session_key}")
        print(f"  👤 Usuario: {self.request.user}")
        
        # FORZAR sesión si no existe
        if not self.request.session.session_key:
            self.request.session.create()
            print(f"  ✅ Sesión creada: {self.request.session.session_key}")
        
        session_key = self.request.session.session_key
        
        # Preparar datos para guardar
        save_data = {}
        
        # Si el usuario está autenticado, asignarlo
        if self.request.user.is_authenticated:
            save_data['usuario'] = self.request.user
            print(f"  👤 Asignando al usuario: {self.request.user.username}")
        
        # Siempre asignar la sesión (para anónimos y autenticados)
        save_data['clave_sesion'] = session_key
        print(f"  🔐 Asignando session key: {session_key}")
        
        # Guardar con los datos adicionales
        serializer.save(**save_data)
        
        print(f"  ✅ Item guardado exitosamente")
    
    def create(self, request, *args, **kwargs):
        """
        Maneja la creación de items en el carrito.
        Si ya existe el producto, incrementa la cantidad.
        """
        print(f"\n🎯 CARRITO - CREATE endpoint llamado")
        print(f"  📨 Data: {request.data}")
        print(f"  🍪 Cookies: {request.COOKIES}")
        print(f"  🆔 Session Key: {request.session.session_key}")
        
        # 1. Verificar que tenemos sesión
        if not request.session.session_key:
            request.session.create()
            print(f"  ✅ Sesión creada: {request.session.session_key}")
        
        session_key = request.session.session_key
        
        # 2. Validar datos básicos
        producto_id = request.data.get('producto')
        cantidad = int(request.data.get('cantidad', 1))
        
        if not producto_id:
            return Response(
                {'error': 'El campo "producto" es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 3. Verificar que el producto existe
        try:
            producto = Producto.objects.get(id=producto_id)
        except Producto.DoesNotExist:
            return Response(
                {'error': f'Producto con ID {producto_id} no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 4. Buscar item existente
        # Para usuarios autenticados: buscar por usuario + producto
        # Para anónimos: buscar por session_key + producto
        if request.user.is_authenticated:
            item_existente = ItemCarrito.objects.filter(
                usuario=request.user,
                producto=producto
            ).first()
        else:
            item_existente = ItemCarrito.objects.filter(
                clave_sesion=session_key,
                producto=producto,
                usuario__isnull=True  # Solo items anónimos
            ).first()
        
        # 5. Si ya existe, actualizar cantidad
        if item_existente:
            print(f"  🔄 Item existente encontrado, actualizando cantidad")
            item_existente.cantidad += cantidad
            item_existente.save()
            
            serializer = self.get_serializer(item_existente)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        # 6. Si no existe, crear nuevo
        print(f"  🆕 Creando nuevo item")
        return super().create(request, *args, **kwargs)

# --- Vistas de Reporte (Plan Estándar) ---
class ReporteView(APIView):
    # RESTRICCIÓN: Reportes requieren Plan Estándar o superior (y rol Gerente/Admin)
    permission_classes = [IsAuthenticated, EsAdminOGerente, PermisoPlanEstandar] 
    
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
    def validate(self, attrs):
        data = super().validate(attrs)
        
        plan_name = 'basico'
        
        print(f"🔍 DEBUG JWT: Usuario: {self.user.username}")
        print(f"🔍 DEBUG JWT: Rol: {self.user.rol}")
        print(f"🔍 DEBUG JWT: Tiene compañía: {bool(self.user.compania)}")
        
        if self.user.compania:
            print(f"🔍 DEBUG JWT: Compañía: {self.user.compania.nombre}")
            
            try:
                # FORMA SEGURA DE OBTENER LA SUSCRIPCIÓN
                suscripcion = getattr(self.user.compania, 'suscripcion', None)
                
                if suscripcion:
                    print(f"🔍 DEBUG JWT: Plan en BD: {suscripcion.plan}")
                    print(f"🔍 DEBUG JWT: Activo: {suscripcion.activo}")
                    
                    if suscripcion.activo:
                        plan_name = suscripcion.plan.lower()
                    else:
                        print("⚠️ DEBUG JWT: Suscripción inactiva")
                else:
                    print("⚠️ DEBUG JWT: No hay objeto suscripción")
                    
            except Suscripcion.DoesNotExist:
                print("⚠️ DEBUG JWT: Suscripcion.DoesNotExist")
            except Exception as e:
                print(f"⚠️ DEBUG JWT: Error: {e}")
        else:
            print("⚠️ DEBUG JWT: Usuario sin compañía")
        
        print(f"🔍 DEBUG JWT: Plan que se envía: {plan_name}")
        
        data.update({
            'username': self.user.username,
            'email': self.user.email,
            'rol': self.user.rol,
            'compania_id': self.user.compania.id if self.user.compania else None,
            'compania_nombre': self.user.compania.nombre if self.user.compania else None,
            'plan': plan_name,
        })
        
        return data
    
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

# --- VISTA DE DIAGNÓSTICO (NUEVA) ---
class DiagnosticoPlanView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        data = {
            'usuario': user.username,
            'rol': user.rol,
            'autenticado': user.is_authenticated,
        }
        
        if user.compania:
            data['compania'] = {
                'id': user.compania.id,
                'nombre': user.compania.nombre,
                'rut': user.compania.rut,
            }
            
            try:
                suscripcion = user.compania.suscripcion
                data['suscripcion'] = {
                    'plan': suscripcion.plan,
                    'activo': suscripcion.activo,
                    'fecha_inicio': suscripcion.fecha_inicio,
                    'fecha_termino': suscripcion.fecha_termino,
                    'max_sucursales': suscripcion.max_sucursales,
                }
                
                # Verificar si el plan es premium
                from django.utils import timezone
                hoy = timezone.now().date()
                data['suscripcion']['valida_hoy'] = suscripcion.fecha_termino >= hoy
                data['suscripcion']['es_premium'] = suscripcion.plan == 'premium'
                data['suscripcion']['acceso_premium'] = (
                    suscripcion.plan == 'premium' and 
                    suscripcion.activo and 
                    suscripcion.fecha_termino >= hoy
                )
            except Suscripcion.DoesNotExist:
                data['suscripcion'] = 'No encontrada'
            except Exception as e:
                data['suscripcion_error'] = str(e)
        
        return Response(data)
    
# --- Vista de Dashboard (sin restricción de plan) ---
class DashboardView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Endpoint simple para datos del dashboard, sin restricción de plan"""
        user = request.user
        compania = user.compania
        
        # Inicializar respuesta
        data = {
            'ventas_mes': 0,
            'transacciones': 0,
            'productos_bajo_stock': 0,
            'ordenes_pendientes': 0,
        }
        
        if not compania:
            return Response(data)
        
        from django.utils import timezone
        hoy = timezone.now()
        inicio_mes = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        try:
            # 1. Ventas del mes (todos pueden ver sus propias ventas)
            ventas = Venta.objects.filter(
                sucursal__compania=compania,
                creado_en__gte=inicio_mes
            )
            
            if user.rol == 'vendedor':
                ventas = ventas.filter(vendedor=user)
            
            data['ventas_mes'] = ventas.aggregate(total=Sum('total'))['total'] or 0
            data['transacciones'] = ventas.count()
            
            # 2. Productos con bajo stock (todos pueden ver inventario)
            productos_bajo_stock = Inventario.objects.filter(
                sucursal__compania=compania,
                stock__lte=F('punto_reorden')
            ).count()
            data['productos_bajo_stock'] = productos_bajo_stock
            
            # 3. Órdenes pendientes (solo si tiene plan premium)
            try:
                suscripcion = compania.suscripcion
                if suscripcion.plan in ['premium'] and suscripcion.activo:
                    ordenes_pendientes = Orden.objects.filter(
                        sucursal__compania=compania,
                        estado='pendiente'
                    ).count()
                    data['ordenes_pendientes'] = ordenes_pendientes
            except Suscripcion.DoesNotExist:
                pass
                
        except Exception as e:
            print(f"Error en dashboard: {e}")
        
        return Response(data)
    
# --- VISTA PARA FUSIONAR CARRITO AL LOGUEARSE ---
class FusionarCarritoView(APIView):
    """Fusiona el carrito de session con el del usuario al loguearse"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        session_key = request.session.session_key
        
        if not session_key:
            return Response({'status': 'No hay session para fusionar'})
        
        # Buscar items en la session actual
        items_session = ItemCarrito.objects.filter(clave_sesion=session_key, usuario__isnull=True)
        
        if not items_session.exists():
            return Response({'status': 'No hay items en session para fusionar'})
        
        items_migrados = 0
        
        for item in items_session:
            # Verificar si ya existe para este usuario
            item_existente = ItemCarrito.objects.filter(
                usuario=user,
                producto=item.producto
            ).first()
            
            if item_existente:
                # Sumar cantidades
                item_existente.cantidad += item.cantidad
                item_existente.save()
                item.delete()  # Eliminar el de session
            else:
                # Migrar a usuario
                item.usuario = user
                item.clave_sesion = None
                item.save()
            
            items_migrados += 1
        
        return Response({
            'status': 'Carrito fusionado',
            'items_migrados': items_migrados
        })