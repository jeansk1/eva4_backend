# core/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import *

class UsuarioAdmin(UserAdmin):
    list_display = ('username', 'email', 'rut', 'rol', 'compania', 'is_active')
    list_filter = ('rol', 'is_active', 'compania')
    fieldsets = UserAdmin.fieldsets + (
        ('Información adicional', {'fields': ('rut', 'rol', 'compania', 'telefono')}),
    )

# Modelos inline
class ItemCompraInline(admin.TabularInline):
    model = ItemCompra
    extra = 1
    min_num = 1

class ItemVentaInline(admin.TabularInline):
    model = ItemVenta
    extra = 1
    min_num = 1

class ItemOrdenInline(admin.TabularInline):
    model = ItemOrden
    extra = 1
    min_num = 1

# Modelos principales
@admin.register(Compania)
class CompaniaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'rut', 'email', 'telefono', 'creado_en')
    search_fields = ('nombre', 'rut')
    list_filter = ('creado_en',)

@admin.register(Suscripcion)
class SuscripcionAdmin(admin.ModelAdmin):
    list_display = ('compania', 'plan', 'fecha_inicio', 'fecha_termino', 'activo', 'max_sucursales')
    list_filter = ('plan', 'activo', 'fecha_inicio')
    list_editable = ('activo',)

@admin.register(Sucursal)
class SucursalAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'compania', 'telefono', 'email', 'creado_en')
    list_filter = ('compania', 'creado_en')
    search_fields = ('nombre', 'compania__nombre')

@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'rut', 'compania', 'contacto', 'telefono', 'email')
    list_filter = ('compania',)
    search_fields = ('nombre', 'rut', 'contacto')

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('sku', 'nombre', 'compania', 'categoria', 'precio', 'costo', 'creado_en')
    list_filter = ('categoria', 'compania', 'creado_en')
    search_fields = ('sku', 'nombre', 'descripcion')
    list_editable = ('precio', 'costo')
    
    def precio_formateado(self, obj):
        return f"${obj.precio:,.0f}"
    precio_formateado.short_description = 'Precio'

@admin.register(Inventario)
class InventarioAdmin(admin.ModelAdmin):
    list_display = ('sucursal', 'producto', 'stock', 'punto_reorden', 'ultima_actualizacion', 'estado_stock')
    list_filter = ('sucursal', 'producto__categoria')
    search_fields = ('producto__nombre', 'producto__sku')
    
    def estado_stock(self, obj):
        if obj.stock <= 0:
            return format_html('<span style="color: red; font-weight: bold;">AGOTADO</span>')
        elif obj.stock <= obj.punto_reorden:
            return format_html('<span style="color: orange; font-weight: bold;">BAJO STOCK</span>')
        else:
            return format_html('<span style="color: green; font-weight: bold;">DISPONIBLE</span>')
    estado_stock.short_description = 'Estado'

@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    inlines = [ItemCompraInline]
    list_display = ('numero_factura', 'proveedor', 'sucursal', 'fecha', 'total_formateado', 'creado_en')
    list_filter = ('proveedor', 'sucursal', 'fecha')
    search_fields = ('numero_factura', 'proveedor__nombre')
    
    def total_formateado(self, obj):
        return f"${obj.total:,.0f}"
    total_formateado.short_description = 'Total'

@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    inlines = [ItemVentaInline]
    list_display = ('id', 'sucursal', 'vendedor', 'total_formateado', 'metodo_pago', 'creado_en')
    list_filter = ('sucursal', 'vendedor', 'metodo_pago', 'creado_en')
    search_fields = ('vendedor__username', 'sucursal__nombre')
    
    def total_formateado(self, obj):
        return f"${obj.total:,.0f}"
    total_formateado.short_description = 'Total'

@admin.register(Orden)
class OrdenAdmin(admin.ModelAdmin):
    inlines = [ItemOrdenInline]
    list_display = ('id', 'nombre_cliente', 'email_cliente', 'total_formateado', 'estado', 'estado_badge', 'creado_en')
    list_filter = ('estado', 'sucursal', 'creado_en')
    list_editable = ('estado',)
    search_fields = ('nombre_cliente', 'email_cliente')
    
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
    estado_badge.short_description = 'Estado'

@admin.register(ItemCarrito)
class ItemCarritoAdmin(admin.ModelAdmin):
    list_display = ('producto', 'usuario', 'cantidad', 'agregado_en')
    list_filter = ('agregado_en',)
    search_fields = ('producto__nombre', 'usuario__username')

# Registrar el resto de modelos
admin.site.register(Usuario, UsuarioAdmin)
admin.site.register(ItemCompra)
admin.site.register(ItemVenta)
admin.site.register(ItemOrden)

# Configuración del admin site
admin.site.site_header = "TemucoSoft - Administración"
admin.site.site_title = "TemucoSoft Admin"
admin.site.index_title = "Bienvenido al Panel de Administración"