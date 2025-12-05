# api/serializers.py - 
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import transaction 
from core.models import *

Usuario = get_user_model()

# --- Funciones de Ayuda (Para no repetir código) ---
def obtener_nombre_seguro(obj, campo):
    """Intenta obtener el nombre de una relación de forma segura"""
    try:
        relacion = getattr(obj, campo)
        if not relacion:
            return "Sin Asignar"
        # Si es un objeto y tiene atributo nombre
        if hasattr(relacion, 'nombre'):
            return relacion.nombre
        # Si es un objeto y tiene username (caso Usuario)
        if hasattr(relacion, 'username'):
            return relacion.username
        # Si por alguna razón es un ID (int)
        return f"ID: {relacion}"
    except:
        return "Error Datos"

# --- Usuario ---
class UsuarioSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    # 👇 ESTE CAMPO AHORA USA LA FUNCIÓN DE PROTECCIÓN 👇
    compania_nombre = serializers.SerializerMethodField()
    
    class Meta:
        model = Usuario
        # El campo 'compania' sigue siendo el ID, pero mostramos el nombre
        fields = ('id', 'username', 'email', 'rut', 'rol', 'compania', 'compania_nombre', 'telefono', 'is_active', 'password', 'creado_en')
        read_only_fields = ('id', 'is_active', 'creado_en', 'compania_nombre') 
        extra_kwargs = {
            'password': {'write_only': True, 'required': False}
        }
        
    # FUNCIÓN PARA OBTENER EL NOMBRE DE LA COMPAÑÍA
    def get_compania_nombre(self, obj):
        # Utilizamos la función segura para obtener el nombre de la empresa
        return obtener_nombre_seguro(obj, 'compania')

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

class SucursalSerializer(serializers.ModelSerializer):
    nombre_compania = serializers.SerializerMethodField()
    class Meta:
        model = Sucursal
        fields = ('id', 'nombre', 'compania', 'nombre_compania', 'direccion', 'telefono', 'email', 'creado_en')
        read_only_fields = ('creado_en',)

    def get_nombre_compania(self, obj):
        return obtener_nombre_seguro(obj, 'compania')

class ProveedorSerializer(serializers.ModelSerializer):
    nombre_compania = serializers.SerializerMethodField()
    class Meta:
        model = Proveedor
        fields = '__all__'

    def get_nombre_compania(self, obj):
        return obtener_nombre_seguro(obj, 'compania')

# --- PRODUCTO (BLINDADO) ---
class ProductoSerializer(serializers.ModelSerializer):
    nombre_compania = serializers.SerializerMethodField()
    class Meta:
        model = Producto
        fields = ('id', 'sku', 'nombre', 'descripcion', 'precio', 'costo', 'categoria', 'imagen', 
                  'compania', 'nombre_compania', 'creado_en', 'actualizado_en')
        read_only_fields = ('creado_en', 'actualizado_en')

    def get_nombre_compania(self, obj):
        return obtener_nombre_seguro(obj, 'compania')

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
    # Agregamos estos campos de lectura para que el frontend tenga datos reales
    nombre_producto = serializers.SerializerMethodField()
    
    class Meta:
        model = ItemVenta
        fields = ('producto', 'nombre_producto', 'cantidad', 'precio_unitario', 'subtotal')
        read_only_fields = ('nombre_producto', 'precio_unitario', 'subtotal')

    def get_nombre_producto(self, obj):
        # Protección por si se borró el producto
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
    # Agregamos este campo para que el frontend sepa qué producto es
    nombre_producto = serializers.SerializerMethodField()

    class Meta:
        model = ItemOrden
        fields = ('producto', 'nombre_producto', 'cantidad', 'precio_unitario')
        read_only_fields = ('nombre_producto',)

    def get_nombre_producto(self, obj):
        # Buscamos el nombre real del producto asociado
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
            # 1. Crear la Orden
            orden = Orden.objects.create(**validated_data)
            
            for item_data in items_data:
                producto = item_data['producto']
                cantidad = item_data['cantidad']
                precio_unitario = item_data['precio_unitario']
                
                # 2. Crear el Item de Orden
                ItemOrden.objects.create(
                    orden=orden, 
                    producto=producto, 
                    cantidad=cantidad, 
                    precio_unitario=precio_unitario
                )
                
                # 3. DESCONTAR STOCK (LÓGICA NUEVA)
                # Buscamos el primer inventario que tenga ese producto y stock suficiente
                # (Como es e-commerce, tomamos de cualquier sucursal disponible si no se especifica una)
                inventario = Inventario.objects.select_for_update().filter(
                    producto=producto, 
                    stock__gte=cantidad
                ).first()
                
                if inventario:
                    inventario.stock -= cantidad
                    inventario.save()
                else:
                    # Si llegamos aquí es porque alguien compró el último justo antes que tú
                    raise serializers.ValidationError(
                        f"No hay stock suficiente para el producto {producto.nombre}"
                    )
            
            return orden

# --- Carrito Interno ---
class ItemCarritoSerializer(serializers.ModelSerializer):
    nombre_producto = serializers.SerializerMethodField()
    precio_producto = serializers.DecimalField(source='producto.precio', read_only=True, max_digits=10, decimal_places=2)
    subtotal = serializers.SerializerMethodField()
    sku_producto = serializers.CharField(source='producto.sku', read_only=True)
    # CORRECCIÓN: Agregamos producto_id para que el frontend pueda leerlo
    producto_id = serializers.PrimaryKeyRelatedField(source='producto', read_only=True)
    imagen_producto = serializers.ImageField(source='producto.imagen', read_only=True)
    
    class Meta:
        model = ItemCarrito
        fields = (
            'id', 
            'producto',         # Se usa para escribir (POST)
            'producto_id',      # Se usa para leer (GET) - CORRECCIÓN
            'nombre_producto',
            'sku_producto',
            'precio_producto',
            'imagen_producto', 
            'cantidad', 
            'subtotal',
            'clave_sesion',
            'usuario',
            'agregado_en'
        )
        read_only_fields = (
            'id', 
            'nombre_producto', 
            'precio_producto', 
            'subtotal',
            'sku_producto',
            'clave_sesion',
            'usuario',
            'agregado_en',
            'producto_id' # CORRECCIÓN
        )
        extra_kwargs = {
            # Mantenemos write_only aquí para el input, pero ya tenemos producto_id para el output
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
        # CORRECCIÓN: Usamos .get() para evitar errores si el campo no viene (updates parciales)
        producto = data.get('producto')
        cantidad = data.get('cantidad')
        
        # 1. Validar producto SOLO si se está enviando (creación o cambio de producto)
        if producto:
            if not Producto.objects.filter(id=producto.id).exists():
                raise serializers.ValidationError({"producto": "Producto no encontrado"})
        
        # 2. Validar cantidad SOLO si se está enviando
        if cantidad is not None:
            if cantidad <= 0:
                raise serializers.ValidationError({"cantidad": "La cantidad debe ser mayor a 0"})
        
        return data
    
    def create(self, validated_data):
        return super().create(validated_data)