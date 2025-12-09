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
    
    def get_permissions(self):
        if self.action in ['create', 'list', 'destroy']:
            return [IsAuthenticated(), EsAdminOGerente()]
        return [IsAuthenticated()] 

    def get_queryset(self):
        usuario = self.request.user
        if usuario.rol == 'super_admin':
            return Usuario.objects.all()
        if usuario.rol == 'admin_cliente':
            return Usuario.objects.filter(compania=usuario.compania)
        return Usuario.objects.filter(id=usuario.id)

    # 🔥 MÉTODO ACTUALIZADO PARA ACEPTAR COMPAÑÍA DE SUPER ADMIN 🔥
    def perform_create(self, serializer):
        usuario_creador = self.request.user
        
        # 1. Si es Super Admin, permitimos que elija la compañía (si viene en el serializer)
        if usuario_creador.rol == 'super_admin':
            # El serializer ya trae los datos del formulario (incluida la 'compania' si se seleccionó)
            serializer.save()
            
        # 2. Si es Admin Cliente o Gerente, FORZAMOS su propia compañía
        elif usuario_creador.compania:
            serializer.save(compania=usuario_creador.compania)
            
        # 3. Caso de borde (no debería pasar si la lógica está bien)
        else:
            serializer.save()

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
        user = self.request.user
        
        # Si el usuario no está logueado o no tiene compañía, no mostramos nada
        if user.is_anonymous or not user.compania:
            # NOTA: Un Super Admin (rol 'super_admin') no tiene compañía, 
            # si quieres que vea TODAS las sucursales, puedes añadir:
            # if user.rol == 'super_admin':
            #    return Sucursal.objects.all()
            return Sucursal.objects.none()
            
        # 🔥 FILTRO CLAVE: Solo devuelve las sucursales que pertenecen a la compañía del usuario
        return Sucursal.objects.filter(compania=user.compania).order_by('nombre')
    
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
    # Permitimos ver a cualquiera autenticado, pero editamos quién ve qué abajo
    permission_classes = [IsAuthenticated, EsAdminOGerente]
    
    def get_queryset(self):
        usuario = self.request.user
        queryset = Producto.objects.all()
        
        # 1. Super Admin: Ve todo el catálogo global
        if usuario.rol == 'super_admin':
            return queryset

        # 2. 🔥 EL FILTRO "TIENDA NUEVA" (Para Dueños y Vendedores con Sucursal)
        # Si el usuario tiene una sucursal asignada (sea dueño o vendedor)...
        if usuario.sucursal:
            # ... SOLO le mostramos los productos que YA existen en SU inventario.
            # Como la sucursal es nueva y no tiene inventario, esto devolverá VACÍO [].
            return queryset.filter(inventario__sucursal=usuario.sucursal).distinct()

        # 3. Dueños Globales (Sin sucursal asignada):
        # Ven todo el catálogo de la compañía (para poder gestionar precios globales, etc.)
        if usuario.compania:
            return queryset.filter(compania=usuario.compania)
            
        return Producto.objects.none()
    
    # 🔥 IMPORTANTE: AL CREAR UN PRODUCTO, LO ASIGNAMOS A LA SUCURSAL AUTOMÁTICAMENTE
    def perform_create(self, serializer):
        # 1. Obtenemos el ID del usuario que viene en el token
        user_id_del_token = self.request.user.id
        
        print(f"\n⚡ INTENTO DE CREACIÓN - ID TOKEN: {user_id_del_token}")

        # 2. TRUCO DE MAGIA: Forzamos una búsqueda fresca en la Base de Datos
        # Esto se salta cualquier caché o token viejo. Vamos directo al disco duro.
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Traemos al usuario "fresco"
        usuario_fresco = User.objects.get(id=user_id_del_token)
        
        print(f"⚡ USUARIO FRESCO: {usuario_fresco.username}")
        print(f"⚡ COMPAÑÍA REAL EN BD: {usuario_fresco.compania} (ID: {usuario_fresco.compania_id})")

        # 3. Validamos usando el usuario fresco
        if not usuario_fresco.compania_id:
            # Si entra aquí, es imposible que en el Shell salga otra cosa.
            # Significa que estás conectado a bases de datos distintas.
            raise serializers.ValidationError(
                {"error": f"IMPOSIBLE: La base de datos dice que el usuario {usuario_fresco.username} NO tiene compañía."}
            )

        # 4. Guardamos usando el usuario fresco
        producto = serializer.save(compania_id=usuario_fresco.compania_id)
        
        # 5. Inventario usando el usuario fresco
        if usuario_fresco.sucursal:
            print(f"⚡ SUCURSAL DETECTADA: {usuario_fresco.sucursal.nombre}")
            Inventario.objects.create(
                sucursal=usuario_fresco.sucursal,
                producto=producto,
                stock=0, 
                punto_reorden=10
            )
        else:
            print("⚡ AVISO: El usuario tiene compañía pero NO tiene sucursal. Producto creado pero no inventariado.")

class InventarioViewSet(viewsets.ModelViewSet):
    queryset = Inventario.objects.all()
    serializer_class = InventarioSerializer
    permission_classes = [IsAuthenticated, EsAdminOGerente] 
    
    def get_queryset(self):
        usuario = self.request.user
        queryset = Inventario.objects.all()

        # ---------------------------------------------------------------
        # 1. NIVEL DIOS: Super Admin ve todo siempre
        # ---------------------------------------------------------------
        if usuario.rol == 'super_admin':
            return Inventario.objects.all()

        # ---------------------------------------------------------------
        # 2. FILTRO DE HIERRO (La solución a tu problema) 🔒
        # ---------------------------------------------------------------
        # No importa si eres Dueño, Gerente o Vendedor. 
        # Si en tu perfil de usuario tienes asignada una 'sucursal', 
        # NO DEBES ver nada más que esa sucursal.
        if usuario.sucursal:
            return queryset.filter(sucursal=usuario.sucursal)

        # ---------------------------------------------------------------
        # 3. DUEÑOS GENERALES (Sin sucursal asignada)
        # ---------------------------------------------------------------
        # Si llegamos aquí, es porque usuario.sucursal es NULL (es un dueño global).
        # Primero filtramos por la compañía para no ver cosas de otros clientes.
        queryset = queryset.filter(sucursal__compania=usuario.compania)
        
        # Luego miramos si eligió alguna sucursal en el menú (?sucursal=X)
        sucursal_id_param = self.request.query_params.get('sucursal', None)

        if sucursal_id_param:
            return queryset.filter(sucursal_id=sucursal_id_param)
        
        # Si es dueño global y no elige sucursal, devolvemos vacío por seguridad
        return Inventario.objects.none()

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
    # Asegúrate de importar IsAuthenticated y EsAdminOVendedor
    permission_classes = [IsAuthenticated, EsAdminOVendedor]
    
    def get_serializer_class(self):
        # Usar serializer detallado para crear (maneja stock), simple para listar
        if self.action in ['create', 'update', 'retrieve']:
            return VentaConItemsSerializer
        return VentaSerializer
    
    def get_queryset(self):
        usuario = self.request.user
        
        # Optimizamos la consulta trayendo datos relacionados de una vez
        queryset = Venta.objects.select_related('sucursal', 'vendedor').all()
        
        # 🔒 LÓGICA DE SEGURIDAD (CANDADO DE ROL)
        
        # 1. Caso Vendedor: Solo ve ventas SUYAS hechas en SU sucursal actual.
        if usuario.rol == 'vendedor':
            # Si el usuario tiene sucursal asignada, filtramos por ella
            if usuario.sucursal:
                queryset = queryset.filter(sucursal=usuario.sucursal)
            
            # Opcional: ¿El vendedor solo ve sus propias ventas o las de todos en su tienda?
            # Si solo debe ver las suyas, descomenta la siguiente línea:
            # queryset = queryset.filter(vendedor=usuario)
            
            # Si no tiene sucursal asignada (error de configuración), no debería ver nada
            if not usuario.sucursal:
                return Venta.objects.none()

        # 2. Caso Admin/Gerente: Ven todo lo de la compañía
        elif usuario.rol in ['admin_cliente', 'gerente']:
            queryset = queryset.filter(sucursal__compania=usuario.compania)
        
        # 3. Caso Super Admin: Ve todo (sin filtro adicional)
        
        # 📊 FILTROS PARA REPORTES Y UI
        sucursal_id = self.request.query_params.get('sucursal', None)
        fecha_desde = self.request.query_params.get('fecha_desde', None)
        fecha_hasta = self.request.query_params.get('fecha_hasta', None)
        
        if sucursal_id:
            # Validamos que el vendedor no intente filtrar una sucursal ajena
            if usuario.rol == 'vendedor' and str(usuario.sucursal.id) != str(sucursal_id):
                # Si intenta ver otra, devolvemos vacío por seguridad
                return Venta.objects.none()
            queryset = queryset.filter(sucursal_id=sucursal_id)
            
        if fecha_desde:
            queryset = queryset.filter(creado_en__date__gte=fecha_desde)
        if fecha_hasta:
            queryset = queryset.filter(creado_en__date__lte=fecha_hasta)
        
        return queryset.order_by('-creado_en') # Ordenamos por más reciente
    
    def perform_create(self, serializer):
        usuario = self.request.user
        
        # 🔒 ASIGNACIÓN AUTOMÁTICA DE SUCURSAL
        # Esto es vital: La venta se guarda en la sucursal del vendedor, 
        # sin importar lo que diga el frontend.
        
        if usuario.rol == 'vendedor' and usuario.sucursal:
            # Vendedor: Forzamos su sucursal asignada
            serializer.save(vendedor=usuario, sucursal=usuario.sucursal)
            
        elif usuario.rol in ['admin_cliente', 'gerente']:
            # Admin/Gerente: Pueden vender, pero debemos verificar la sucursal
            sucursal_id = self.request.data.get('sucursal')
            
            if sucursal_id:
                # Si mandan ID, usamos esa sucursal (verificando que sea de su compañia)
                serializer.save(vendedor=usuario) # El serializer valida la pertenencia de la sucursal
            else:
                # Si no mandan ID y tienen sucursal asignada en perfil, usamos esa
                if usuario.sucursal:
                    serializer.save(vendedor=usuario, sucursal=usuario.sucursal)
                else:
                    # Si no hay sucursal por ningún lado, el serializer lanzará error de validación
                    serializer.save(vendedor=usuario)
        else:
            # Fallback
            serializer.save(vendedor=usuario)

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
    Maneja la lógica de sumar cantidades si el producto ya existe.
    """
    queryset = ItemCarrito.objects.all()
    serializer_class = ItemCarritoSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        """Devuelve los items del usuario o de la sesión anónima"""
        if not self.request.session.session_key:
            self.request.session.create()
            
        session_key = self.request.session.session_key
        
        if self.request.user.is_authenticated:
            # Si el usuario entra, mostramos sus items + los de su sesión actual
            return ItemCarrito.objects.filter(
                Q(usuario=self.request.user) | Q(clave_sesion=session_key)
            ).order_by('-agregado_en')
        else:
            # Usuario anónimo
            return ItemCarrito.objects.filter(clave_sesion=session_key).order_by('-agregado_en')
    
    def perform_create(self, serializer):
        """Asigna usuario o sesión al guardar"""
        if not self.request.session.session_key:
            self.request.session.create()
        
        session_key = self.request.session.session_key
        save_data = {'clave_sesion': session_key}
        
        if self.request.user.is_authenticated:
            save_data['usuario'] = self.request.user
            
        serializer.save(**save_data)

    def create(self, request, *args, **kwargs):
        """
        Lógica personalizada: Si el producto ya existe en el carrito, SUMA la cantidad.
        """
        try:
            # 1. Obtener datos limpios
            producto_id = int(request.data.get('producto'))
            cantidad = int(request.data.get('cantidad', 1))
        except (ValueError, TypeError):
            return Response({'error': 'Datos inválidos'}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Asegurar sesión
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key
        user = request.user

        # 3. Buscar si YA existe este producto en el carrito del usuario/sesión
        query = Q(producto_id=producto_id)
        
        if user.is_authenticated:
            # Busca por usuario O por sesión (para atrapar items justo antes del login)
            query &= (Q(usuario=user) | Q(clave_sesion=session_key))
        else:
            query &= Q(clave_sesion=session_key)

        # Buscamos el item más reciente que coincida
        item_existente = ItemCarrito.objects.filter(query).first()

        # 4. Lógica de Fusión
        if item_existente:
            print(f"🔄 Producto {producto_id} ya existe. Sumando {cantidad} unidades.")
            
            # Actualizamos cantidad
            item_existente.cantidad += cantidad
            
            # Si el usuario está logueado pero el item era anónimo, nos lo "apropiamos"
            if user.is_authenticated and not item_existente.usuario:
                item_existente.usuario = user
            
            item_existente.save()
            
            # Devolvemos el item actualizado
            serializer = self.get_serializer(item_existente)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # 5. Si no existe, creamos uno nuevo (comportamiento normal)
        print(f"🆕 Creando nuevo item para producto {producto_id}")
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