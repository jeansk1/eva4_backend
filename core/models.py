# core/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.utils import timezone
# Importamos los validadores desde el archivo externo para no ensuciar el modelo
from .validators import validar_rut_chileno, validar_rut, validar_fecha_no_futura, validar_numero_positivo

class Usuario(AbstractUser):
    ROL_CHOICES = [
        ('super_admin', 'Super Administrador'),
        ('admin_cliente', 'Administrador Cliente'),
        ('gerente', 'Gerente'),
        ('vendedor', 'Vendedor'),
        ('cliente_final', 'Cliente Final'),
    ]
    
    rut = models.CharField(
        max_length=12, 
        unique=True, 
        validators=[validar_rut_chileno],
        help_text='RUT chileno (formato: 12.345.678-9)'
    )
    rol = models.CharField(max_length=20, choices=ROL_CHOICES, default='vendedor')
    compania = models.ForeignKey('Compania', on_delete=models.SET_NULL, null=True, blank=True)
    telefono = models.CharField(max_length=15, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    def clean(self):
        # Validar que super_admin no tenga compañía
        if self.rol == 'super_admin' and self.compania:
            raise ValidationError('El super administrador no debe tener compañía asignada')
        
        # Validar que otros roles tengan compañía
        if self.rol != 'super_admin' and not self.compania:
            raise ValidationError(f'El rol {self.rol} debe tener una compañía asignada')
    
    def __str__(self):
        return f"{self.username} ({self.get_rol_display()})"
    
    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        permissions = [
            ("puede_crear_usuarios", "Puede crear nuevos usuarios"),
            ("puede_ver_reportes", "Puede ver reportes"),
            ("puede_gestionar_inventario", "Puede gestionar inventario"),
        ]

class Compania(models.Model):
    nombre = models.CharField(max_length=100)
    rut = models.CharField(max_length=12, validators=[validar_rut])
    direccion = models.TextField()
    telefono = models.CharField(max_length=15)
    email = models.EmailField()
    creado_en = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.nombre
    
    class Meta:
        verbose_name = 'Compañía'
        verbose_name_plural = 'Compañías'

class Suscripcion(models.Model):
    PLAN_CHOICES = [
        ('basico', 'Básico'),
        ('estandar', 'Estándar'),
        ('premium', 'Premium'),
    ]
    
    compania = models.OneToOneField(Compania, on_delete=models.CASCADE)
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES)
    fecha_inicio = models.DateField()
    fecha_termino = models.DateField()
    activo = models.BooleanField(default=True)
    max_sucursales = models.IntegerField(default=1)
    
    def clean(self):
        if self.fecha_termino <= self.fecha_inicio:
            raise ValidationError('La fecha de término debe ser posterior a la de inicio')
    
    # 🔥 AGREGA ESTE MÉTODO SAVE() 🔥
    def save(self, *args, **kwargs):
        # Asignar límites automáticos según el plan
        if self.plan == 'basico':
            self.max_sucursales = 1
        elif self.plan == 'estandar':
            self.max_sucursales = 3
        elif self.plan == 'premium':
            self.max_sucursales = 9999  # Prácticamente ilimitado
        
        # Llamar al save original
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.compania.nombre} - {self.get_plan_display()}"
    
    class Meta:
        verbose_name = 'Suscripción'
        verbose_name_plural = 'Suscripciones'

class Sucursal(models.Model):
    compania = models.ForeignKey(Compania, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100)
    direccion = models.TextField()
    telefono = models.CharField(max_length=15)
    email = models.EmailField()
    creado_en = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.nombre} - {self.compania.nombre}"
    
    class Meta:
        verbose_name = 'Sucursal'
        verbose_name_plural = 'Sucursales'

class Proveedor(models.Model):
    compania = models.ForeignKey(Compania, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100)
    rut = models.CharField(max_length=12, validators=[validar_rut])
    contacto = models.CharField(max_length=100)
    telefono = models.CharField(max_length=15)
    email = models.EmailField()
    direccion = models.TextField()
    creado_en = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.nombre
    
    class Meta:
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'

class Producto(models.Model):
    CATEGORIA_CHOICES = [
        ('electronica', 'Electrónica'),
        ('ropa', 'Ropa'),
        ('alimentos', 'Alimentos'),
        ('bebidas', 'Bebidas'),
        ('limpieza', 'Limpieza'),
        ('otros', 'Otros'),
    ]
    
    compania = models.ForeignKey(Compania, on_delete=models.CASCADE)
    sku = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    costo = models.DecimalField(max_digits=10, decimal_places=2)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES)
    imagen = models.ImageField(upload_to='productos/', null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    def clean(self):
        if self.precio < 0:
            raise ValidationError('El precio no puede ser negativo')
        if self.costo < 0:
            raise ValidationError('El costo no puede ser negativo')
    
    def __str__(self):
        return f"{self.sku} - {self.nombre}"
    
    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'

class Inventario(models.Model):
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    stock = models.IntegerField(default=0)
    punto_reorden = models.IntegerField(default=10)
    ultima_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('sucursal', 'producto')
        verbose_name = 'Inventario'
        verbose_name_plural = 'Inventarios'
    
    def clean(self):
        if self.stock < 0:
            raise ValidationError('El stock no puede ser negativo')
    
    def __str__(self):
        return f"{self.sucursal.nombre} - {self.producto.nombre}: {self.stock}"

class Compra(models.Model):
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT)
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE)
    numero_factura = models.CharField(max_length=50)
    fecha = models.DateField()
    total = models.DecimalField(max_digits=10, decimal_places=2)
    creado_en = models.DateTimeField(auto_now_add=True)
    
    def clean(self):
        if self.fecha > timezone.now().date():
            raise ValidationError('La fecha de compra no puede ser futura')
    
    def __str__(self):
        return f"Compra #{self.numero_factura} - {self.proveedor.nombre}"
    
    class Meta:
        verbose_name = 'Compra'
        verbose_name_plural = 'Compras'

class ItemCompra(models.Model):
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name='items')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    
    def clean(self):
        if self.cantidad <= 0:
            raise ValidationError('La cantidad debe ser mayor a 0')
    
    class Meta:
        verbose_name = 'Item de Compra'
        verbose_name_plural = 'Items de Compra'

class Venta(models.Model):
    METODO_PAGO_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('debito', 'Tarjeta Débito'),
        ('credito', 'Tarjeta Crédito'),
        ('transferencia', 'Transferencia'),
    ]
    
    sucursal = models.ForeignKey(Sucursal, on_delete=models.CASCADE)
    vendedor = models.ForeignKey(Usuario, on_delete=models.PROTECT, limit_choices_to={'rol': 'vendedor'})
    total = models.DecimalField(max_digits=10, decimal_places=2)
    metodo_pago = models.CharField(max_length=20, choices=METODO_PAGO_CHOICES)
    creado_en = models.DateTimeField(auto_now_add=True)
    
    def clean(self):
        if self.creado_en and self.creado_en > timezone.now():
            raise ValidationError('La fecha de venta no puede ser futura')
        
        # Validar que el vendedor tenga rol vendedor
        if self.vendedor.rol != 'vendedor':
            raise ValidationError('El vendedor debe tener rol "vendedor"')
    
    def save(self, *args, **kwargs):
        # Calcular total automáticamente si hay items (útil para admin panel)
        # Nota: La API maneja esto explícitamente en el serializer.
        if not self.total and self.pk and hasattr(self, 'items'):
             self.total = sum(item.subtotal for item in self.items.all())
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Venta #{self.id} - {self.sucursal.nombre}"
    
    class Meta:
        verbose_name = 'Venta'
        verbose_name_plural = 'Ventas'

class ItemVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='items')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    
    def clean(self):
        if self.cantidad <= 0:
            raise ValidationError('La cantidad debe ser mayor a 0')
    
    class Meta:
        verbose_name = 'Item de Venta'
        verbose_name_plural = 'Items de Venta'

class Orden(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('procesando', 'Procesando'),
        ('enviado', 'Enviado'),
        ('entregado', 'Entregado'),
        ('cancelado', 'Cancelado'),
    ]
    
    nombre_cliente = models.CharField(max_length=100)
    email_cliente = models.EmailField()
    telefono_cliente = models.CharField(max_length=15, blank=True)
    direccion_cliente = models.TextField()
    total = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    sucursal = models.ForeignKey(Sucursal, on_delete=models.SET_NULL, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Orden #{self.id} - {self.nombre_cliente}"
    
    class Meta:
        verbose_name = 'Orden'
        verbose_name_plural = 'Órdenes'

class ItemOrden(models.Model):
    orden = models.ForeignKey(Orden, on_delete=models.CASCADE, related_name='items')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    
    def clean(self):
        if self.cantidad <= 0:
            raise ValidationError('La cantidad debe ser mayor a 0')
    
    class Meta:
        verbose_name = 'Item de Orden'
        verbose_name_plural = 'Items de Orden'

class ItemCarrito(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, null=True, blank=True)
    clave_sesion = models.CharField(max_length=100, null=True, blank=True)  # Para usuarios anónimos
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.IntegerField(default=1)
    agregado_en = models.DateTimeField(auto_now_add=True)
    
    def clean(self):
        if self.cantidad <= 0:
            raise ValidationError('La cantidad debe ser mayor a 0')
    
    def __str__(self):
        usuario_str = self.usuario.username if self.usuario else f"Anónimo({self.clave_sesion[:8]}...)"
        return f"{self.producto.nombre} x{self.cantidad} - {usuario_str}"
    
    class Meta:
        verbose_name = 'Item de Carrito'
        verbose_name_plural = 'Items de Carrito'