# core/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import *

# --- 1. Configuración de Usuario ---
class UsuarioAdmin(UserAdmin):
    list_display = ('username', 'email', 'rut', 'rol', 'compania', 'sucursal', 'is_active')
    list_filter = ('rol', 'is_active', 'compania')
    # Optimización: Carga la compañía y sucursal en la misma consulta
    list_select_related = ('compania', 'sucursal')
    search_fields = ('username', 'email', 'rut') # Necesario para autocomplete
    
    fieldsets = UserAdmin.fieldsets + (
        ('Información corporativa', {'fields': ('rut', 'rol', 'compania', 'sucursal', 'telefono')}),
    )

# --- 2. Inlines (Detalles dentro de otros formularios) ---
class ItemCompraInline(admin.TabularInline):
    model = ItemCompra
    extra = 1
    min_num = 1
    # Usamos autocomplete para no cargar todos los productos en el dropdown
    autocomplete_fields = ['producto']

class ItemVentaInline(admin.TabularInline):
    model = ItemVenta
    extra = 0 # No mostrar filas vacías extra para ahorrar espacio
    min_num = 1
    autocomplete_fields = ['producto']
    # Hacemos los items de venta solo lectura para preservar historia
    readonly_fields = ('producto', 'cantidad', 'precio_unitario', 'subtotal')
    can_delete = False

class ItemOrdenInline(admin.TabularInline):
    model = ItemOrden
    extra = 0
    min_num = 1
    autocomplete_fields = ['producto']

# --- 3. Modelos Principales ---

@admin.register(Compania)
class CompaniaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'rut', 'email', 'telefono', 'creado_en')
    search_fields = ('nombre', 'rut') # Habilita búsqueda para otros modelos
    list_filter = ('creado_en',)

@admin.register(Suscripcion)
class SuscripcionAdmin(admin.ModelAdmin):
    # CORREGIDO: Agregamos 'activo' explícitamente para que list_editable funcione
    list_display = ('compania', 'plan', 'activo', 'fecha_inicio', 'fecha_termino', 'max_sucursales', 'estado_badge')
    list_filter = ('plan', 'activo', 'fecha_termino')
    list_editable = ('activo',) # Ahora sí funciona porque 'activo' está arriba
    list_select_related = ('compania',)
    autocomplete_fields = ['compania']

    def estado_badge(self, obj):
        if obj.activo:
            return format_html('<span style="color: green;">✔</span>')
        return format_html('<span style="color: red;">✘</span>')
    estado_badge.short_description = 'Visual'

@admin.register(Sucursal)
class SucursalAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'compania', 'telefono', 'email', 'creado_en')
    list_filter = ('compania', 'creado_en')
    search_fields = ('nombre', 'compania__nombre')
    list_select_related = ('compania',)
    autocomplete_fields = ['compania']

@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'rut', 'compania', 'contacto', 'telefono')
    list_filter = ('compania',)
    search_fields = ('nombre', 'rut', 'contacto')
    list_select_related = ('compania',)

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    # CORREGIDO: Cambiamos 'precio_formateado' por 'precio' para poder editarlo
    list_display = ('sku', 'nombre', 'compania', 'categoria', 'precio', 'costo', 'stock_total')
    list_filter = ('categoria', 'compania', 'creado_en')
    search_fields = ('sku', 'nombre', 'descripcion')
    
    # Esto ahora funcionará porque 'precio' y 'costo' están en list_display
    list_editable = ('precio', 'costo') 
    
    list_select_related = ('compania',)
    
    def stock_total(self, obj):
        return obj.inventario_set.aggregate(total=models.Sum('stock'))['total'] or 0
    stock_total.short_description = 'Stock Global'

@admin.register(Inventario)
class InventarioAdmin(admin.ModelAdmin):
    list_display = ('sucursal', 'producto', 'stock', 'punto_reorden', 'ultima_actualizacion', 'estado_stock')
    list_filter = ('sucursal__compania', 'sucursal', 'producto__categoria')
    search_fields = ('producto__nombre', 'producto__sku')
    
    # 🔥 OPTIMIZACIONES CLAVE
    list_select_related = ('sucursal', 'producto') 
    autocomplete_fields = ['sucursal', 'producto'] 
    list_editable = ('stock', 'punto_reorden') # Edición rápida estilo Excel
    
    def estado_stock(self, obj):
        if obj.stock <= 0:
            return format_html('<span style="color: white; background-color: red; padding: 3px 8px; border-radius: 4px; font-weight: bold;">AGOTADO</span>')
        elif obj.stock <= obj.punto_reorden:
            return format_html('<span style="color: black; background-color: orange; padding: 3px 8px; border-radius: 4px; font-weight: bold;">BAJO STOCK</span>')
        else:
            return format_html('<span style="color: green; font-weight: bold;">DISPONIBLE</span>')
    estado_stock.short_description = 'Estado'

@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    inlines = [ItemCompraInline]
    list_display = ('numero_factura', 'proveedor', 'sucursal', 'fecha', 'total_formateado')
    list_filter = ('sucursal__compania', 'fecha')
    search_fields = ('numero_factura', 'proveedor__nombre')
    
    list_select_related = ('proveedor', 'sucursal')
    autocomplete_fields = ['proveedor', 'sucursal']
    
    def total_formateado(self, obj):
        return f"${obj.total:,.0f}"
    total_formateado.short_description = 'Total'

@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    inlines = [ItemVentaInline]
    list_display = ('id', 'sucursal', 'vendedor', 'total_formateado', 'metodo_pago', 'creado_en')
    list_filter = ('sucursal__compania', 'metodo_pago', 'creado_en')
    search_fields = ('vendedor__username', 'sucursal__nombre', 'id')
    
    # Optimización y Seguridad
    list_select_related = ('sucursal', 'vendedor')
    autocomplete_fields = ('sucursal', 'vendedor')
    
    # Protegemos la integridad de las ventas históricas
    readonly_fields = ('total', 'sucursal', 'vendedor', 'metodo_pago', 'creado_en')
    
    def total_formateado(self, obj):
        return f"${obj.total:,.0f}"
    total_formateado.short_description = 'Total'
    
    def has_delete_permission(self, request, obj=None):
        # Opcional: Evitar borrar ventas desde el admin para no descuadrar caja
        if request.user.is_superuser:
            return True
        return False

@admin.register(Orden)
class OrdenAdmin(admin.ModelAdmin):
    inlines = [ItemOrdenInline]
    list_display = ('id', 'nombre_cliente', 'total_formateado', 'estado', 'estado_badge', 'sucursal', 'creado_en')
    list_filter = ('estado', 'sucursal', 'creado_en')
    list_editable = ('estado',)
    search_fields = ('nombre_cliente', 'email_cliente', 'id')
    
    list_select_related = ('sucursal',)
    autocomplete_fields = ['sucursal']
    
    def total_formateado(self, obj):
        return f"${obj.total:,.0f}"
    total_formateado.short_description = 'Total'
    
    def estado_badge(self, obj):
        colores = {
            'pendiente': 'gray',
            'procesando': 'blue',
            'enviado': 'orange',
            'entregado': 'green',
            'cancelado': 'red',
        }
        color = colores.get(obj.estado, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 10px; font-weight: bold;">{}</span>',
            color, obj.get_estado_display().upper()
        )
    estado_badge.short_description = 'Badge'

@admin.register(ItemCarrito)
class ItemCarritoAdmin(admin.ModelAdmin):
    list_display = ('producto', 'usuario', 'cantidad', 'agregado_en', 'clave_sesion')
    list_filter = ('agregado_en',)
    search_fields = ('producto__nombre', 'usuario__username')
    list_select_related = ('producto', 'usuario')

# Registrar el Usuario personalizado
admin.site.register(Usuario, UsuarioAdmin)

# Configuración del encabezado del panel
admin.site.site_header = "TemucoSoft - Administración"
admin.site.site_title = "TemucoSoft Admin"
admin.site.index_title = "Panel de Control SaaS"