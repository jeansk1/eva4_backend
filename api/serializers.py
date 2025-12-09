from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import transaction 
from core.models import *

Usuario = get_user_model()

# --- Funciones de Ayuda ---
def obtener_nombre_seguro(obj, campo):
    """Intenta obtener el nombre de una relación de forma segura"""
    try:
        relacion = getattr(obj, campo)
        if not relacion:
            return "Sin Asignar"
        if hasattr(relacion, 'nombre'):
            return relacion.nombre
        if hasattr(relacion, 'username'):
            return relacion.username
        return f"ID: {relacion}"
    except:
        return "Error Datos"

# --- Usuario ---
class UsuarioSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    compania_nombre = serializers.SerializerMethodField()
    sucursal_nombre = serializers.SerializerMethodField()
    
    class Meta:
        model = Usuario
        fields = ('id', 'username', 'email', 'rut', 'rol', 'compania', 'compania_nombre', 'sucursal', 'sucursal_nombre', 'telefono', 'is_active', 'password', 'creado_en')
        read_only_fields = ('id', 'is_active', 'creado_en', 'compania_nombre', 'sucursal_nombre') 
        
        # 🔥 AGREGA ESTO: Hacemos que 'compania' no sea obligatoria en el JSON de entrada
        extra_kwargs = {
            'password': {'write_only': True, 'required': False},
            'compania': {'required': False, 'allow_null': True} 
        }
        
    def get_compania_nombre(self, obj):
        return obtener_nombre_seguro(obj, 'compania')

    def get_sucursal_nombre(self, obj):
        return obtener_nombre_seguro(obj, 'sucursal')

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        usuario = Usuario(**validated_data)
        if password:
            usuario.set_password(password)
        usuario.save()
        return usuario
    
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance

# --- Modelos Base ---
class CompaniaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Compania
        fields = '__all__'

class SuscripcionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Suscripcion
        fields = '__all__'

# 🔥 CORRECCIÓN AQUÍ: SucursalSerializer 🔥
class SucursalSerializer(serializers.ModelSerializer):
    nombre_compania = serializers.SerializerMethodField()
    class Meta:
        model = Sucursal
        fields = ('id', 'nombre', 'compania', 'nombre_compania', 'direccion', 'telefono', 'email', 'creado_en')
        # AGREGAMOS 'compania' A READ_ONLY PARA QUE NO LO PIDA EN EL FORMULARIO
        read_only_fields = ('creado_en', 'compania')

    def get_nombre_compania(self, obj):
        return obtener_nombre_seguro(obj, 'compania')

# 🔥 CORRECCIÓN AQUÍ: ProveedorSerializer 🔥
class ProveedorSerializer(serializers.ModelSerializer):
    nombre_compania = serializers.SerializerMethodField()
    class Meta:
        model = Proveedor
        fields = '__all__'
        # AGREGAMOS 'compania' AQUÍ TAMBIÉN
        read_only_fields = ('compania',)

    def get_nombre_compania(self, obj):
        return obtener_nombre_seguro(obj, 'compania')

# 🔥 CORRECCIÓN AQUÍ: ProductoSerializer 🔥
class ProductoSerializer(serializers.ModelSerializer):
    # Agrega esto si quieres que el nombre salga en la respuesta JSON
    nombre_compania = serializers.SerializerMethodField() 

    class Meta:
        model = Producto
        fields = '__all__'
        # ESTO ESTÁ PERFECTO: Protege el campo para que no se pida al crear
        read_only_fields = ('compania', 'creado_en', 'actualizado_en')

    def get_nombre_compania(self, obj):
        # Asegúrate de importar obtener_nombre_seguro o usar try/except
        if obj.compania:
            return obj.compania.nombre
        return "Sin Compañía"

class InventarioSerializer(serializers.ModelSerializer):
    nombre_producto = serializers.SerializerMethodField()
    nombre_sucursal = serializers.SerializerMethodField()
    class Meta:
        model = Inventario
        fields = ('id', 'sucursal', 'nombre_sucursal', 'producto', 'nombre_producto', 
                  'stock', 'punto_reorden', 'ultima_actualizacion')

    def get_nombre_producto(self, obj):
        return obtener_nombre_seguro(obj, 'producto')

    def get_nombre_sucursal(self, obj):
        return obtener_nombre_seguro(obj, 'sucursal')

# --- Compra y Stock ---
class ItemCompraSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemCompra
        fields = ('producto', 'cantidad', 'precio_unitario') 

class CompraSerializer(serializers.ModelSerializer):
    items = ItemCompraSerializer(many=True)
    nombre_proveedor = serializers.SerializerMethodField()
    nombre_sucursal = serializers.SerializerMethodField()
    
    class Meta:
        model = Compra
        fields = ('id', 'proveedor', 'nombre_proveedor', 'sucursal', 'nombre_sucursal', 
                  'numero_factura', 'fecha', 'total', 'items', 'creado_en')
        read_only_fields = ('total', 'creado_en')

    def get_nombre_proveedor(self, obj):
        return obtener_nombre_seguro(obj, 'proveedor')

    def get_nombre_sucursal(self, obj):
        return obtener_nombre_seguro(obj, 'sucursal')

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        with transaction.atomic():
            compra = Compra.objects.create(total=0, **validated_data) 
            total_compra = 0
            for item_data in items_data:
                producto = item_data['producto']
                cantidad = item_data['cantidad']
                precio_unitario = item_data['precio_unitario']
                subtotal = cantidad * precio_unitario
                ItemCompra.objects.create(compra=compra, producto=producto, cantidad=cantidad, precio_unitario=precio_unitario, subtotal=subtotal)
                
                # AUMENTAR STOCK
                inventario, created = Inventario.objects.get_or_create(
                    sucursal=compra.sucursal, producto=producto, defaults={'stock': 0}
                )
                inventario.stock += cantidad
                inventario.save()
                total_compra += subtotal
            compra.total = total_compra
            compra.save()
            return compra

# --- Venta y Stock ---
class VentaSerializer(serializers.ModelSerializer):
    nombre_sucursal = serializers.SerializerMethodField()
    nombre_vendedor = serializers.SerializerMethodField()
    class Meta:
        model = Venta
        fields = ('id', 'sucursal', 'nombre_sucursal', 'vendedor', 'nombre_vendedor', 'total', 'metodo_pago', 'creado_en')
        read_only_fields = ('total', 'creado_en')

    def get_nombre_sucursal(self, obj):
        return obtener_nombre_seguro(obj, 'sucursal')

    def get_nombre_vendedor(self, obj):
        return obtener_nombre_seguro(obj, 'vendedor')

class ItemVentaSerializer(serializers.ModelSerializer):
    nombre_producto = serializers.SerializerMethodField()
    
    class Meta:
        model = ItemVenta
        fields = ('producto', 'nombre_producto', 'cantidad', 'precio_unitario', 'subtotal')
        read_only_fields = ('nombre_producto', 'precio_unitario', 'subtotal')

    def get_nombre_producto(self, obj):
        return obj.producto.nombre if obj.producto else "Producto Eliminado"
        
class VentaConItemsSerializer(serializers.ModelSerializer):
    items = ItemVentaSerializer(many=True)
    nombre_sucursal = serializers.SerializerMethodField()
    nombre_vendedor = serializers.SerializerMethodField()
    class Meta:
        model = Venta
        fields = ('id', 'sucursal', 'nombre_sucursal', 'vendedor', 'nombre_vendedor', 'total', 'metodo_pago', 'items', 'creado_en')
        read_only_fields = ('total', 'creado_en', 'vendedor')

    def get_nombre_sucursal(self, obj):
        return obtener_nombre_seguro(obj, 'sucursal')

    def get_nombre_vendedor(self, obj):
        return obtener_nombre_seguro(obj, 'vendedor')
    
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        with transaction.atomic(): 
            venta = Venta.objects.create(total=0, **validated_data)
            total_venta = 0
            for item_data in items_data:
                producto = item_data['producto']
                cantidad = item_data['cantidad']
                precio_unitario = producto.precio
                # Descontar Stock
                inventario = Inventario.objects.select_for_update().filter(sucursal=venta.sucursal, producto=producto).first()
                if not inventario or inventario.stock < cantidad:
                    raise serializers.ValidationError(f'Stock insuficiente para {producto.nombre}')
                inventario.stock -= cantidad
                inventario.save()
                subtotal = cantidad * precio_unitario
                ItemVenta.objects.create(venta=venta, producto=producto, cantidad=cantidad, precio_unitario=precio_unitario, subtotal=subtotal)
                total_venta += subtotal
            venta.total = total_venta
            venta.save()
            return venta

# --- Órdenes ---
class ItemOrdenSerializer(serializers.ModelSerializer):
    nombre_producto = serializers.SerializerMethodField()

    class Meta:
        model = ItemOrden
        fields = ('producto', 'nombre_producto', 'cantidad', 'precio_unitario')
        read_only_fields = ('nombre_producto',)

    def get_nombre_producto(self, obj):
        return obj.producto.nombre if obj.producto else "Producto Eliminado"

class OrdenSerializer(serializers.ModelSerializer):
    items = ItemOrdenSerializer(many=True) 
    nombre_sucursal = serializers.SerializerMethodField()
    class Meta:
        model = Orden
        fields = '__all__'

    def get_nombre_sucursal(self, obj):
        return obtener_nombre_seguro(obj, 'sucursal')

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        with transaction.atomic():
            orden = Orden.objects.create(**validated_data)
            for item_data in items_data:
                # LÓGICA DE STOCK (AGREGADA EN PASOS ANTERIORES)
                producto = item_data['producto']
                cantidad = item_data['cantidad']
                precio_unitario = item_data['precio_unitario']
                
                # Descontar stock de cualquier sucursal disponible (E-commerce global)
                inventario = Inventario.objects.select_for_update().filter(producto=producto, stock__gte=cantidad).first()
                
                if inventario:
                    inventario.stock -= cantidad
                    inventario.save()
                # Nota: Si no hay inventario, se crea la orden igual (backorder) o se lanza error según regla de negocio.
                # Aquí permitimos crearla, pero idealmente se validó antes en el frontend.
                
                ItemOrden.objects.create(orden=orden, **item_data)
            return orden

# --- Carrito Interno ---
class ItemCarritoSerializer(serializers.ModelSerializer):
    nombre_producto = serializers.SerializerMethodField()
    precio_producto = serializers.DecimalField(source='producto.precio', read_only=True, max_digits=10, decimal_places=2)
    subtotal = serializers.SerializerMethodField()
    sku_producto = serializers.CharField(source='producto.sku', read_only=True)
    producto_id = serializers.PrimaryKeyRelatedField(source='producto', read_only=True)
    imagen_producto = serializers.ImageField(source='producto.imagen', read_only=True)
    
    class Meta:
        model = ItemCarrito
        fields = (
            'id', 'producto', 'producto_id', 'nombre_producto', 'sku_producto',
            'precio_producto', 'imagen_producto', 'cantidad', 'subtotal',
            'clave_sesion', 'usuario', 'agregado_en'
        )
        read_only_fields = (
            'id', 'nombre_producto', 'precio_producto', 'subtotal',
            'sku_producto', 'clave_sesion', 'usuario', 'agregado_en',
            'producto_id', 'imagen_producto'
        )
        extra_kwargs = {
            'producto': {'required': True, 'write_only': True},
            'cantidad': {'required': True, 'min_value': 1}
        }
    
    def get_nombre_producto(self, obj):
        return obtener_nombre_seguro(obj, 'producto')

    def get_subtotal(self, obj):
        if obj.producto and hasattr(obj.producto, 'precio'):
            return obj.cantidad * obj.producto.precio
        return 0
    
    def validate(self, data):
        """Validaciones adicionales"""
        # CORRECCIÓN: .get() para actualizaciones parciales
        producto = data.get('producto')
        cantidad = data.get('cantidad')
        
        if producto:
            if not Producto.objects.filter(id=producto.id).exists():
                raise serializers.ValidationError({"producto": "Producto no encontrado"})
        
        if cantidad is not None:
            if cantidad <= 0:
                raise serializers.ValidationError({"cantidad": "La cantidad debe ser mayor a 0"})
        
        return data
    
    def create(self, validated_data):
        return super().create(validated_data)