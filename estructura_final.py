import os

# Estructura completa de templates
estructura = {
    'templates': {
        'productos': [
            'list.html',      # Ya tienes
            'detail.html',    # Ya tienes
            'create.html',
            'edit.html'
        ],
        'sucursales': [
            'list.html',      # Ya tienes
            'detail.html',
            'create.html'
        ],
        'proveedores': [
            'list.html',      # Ya tienes  
            'detail.html',
            'create.html'
        ],
        'inventario': [
            'list.html',      # Ya tienes
            'ajustar.html',
            'movimientos.html'
        ],
        'ventas': [           # Cambié pos/ por ventas/
            'nueva.html',     # Antes: pos/sale.html
            'historial.html', # Antes: pos/history.html
            'recibo.html'
        ],
        'reportes': [
            'dashboard.html', # Ya tienes
            'ventas.html',    # Ya tienes
            'stock.html',
            'proveedores.html'
        ],
        'usuarios': [
            'list.html',      # Ya tienes
            'crear.html',
            'perfil.html'
        ],
        'tienda': [           # Cambié shop/ por tienda/
            'catalogo.html',  # Antes: shop/catalog.html
            'carrito.html',   # Antes: shop/cart.html
            'pago.html',      # Antes: shop/checkout.html
            'producto_detalle.html',  # Antes: shop/product_detail.html
            'confirmacion.html'
        ]
    }
}

def crear_estructura():
    base_dir = 'templates'
    
    for carpeta, archivos in estructura.items():
        if carpeta == 'templates':
            for subcarpeta, subarchivos in archivos.items():
                ruta_carpeta = os.path.join(base_dir, subcarpeta)
                os.makedirs(ruta_carpeta, exist_ok=True)
                print(f"📁 Carpeta creada: {ruta_carpeta}")
                
                for archivo in subarchivos:
                    ruta_archivo = os.path.join(ruta_carpeta, archivo)
                    if not os.path.exists(ruta_archivo):
                        with open(ruta_archivo, 'w', encoding='utf-8') as f:
                            # Contenido básico
                            if 'list.html' in archivo:
                                f.write(f"""{{% extends 'base.html' %}}

{{% block title %}}{subcarpeta.capitalize()} - TemucoSoft{{% endblock %}}

{{% block page_title %}}{'Gestión de' if subcarpeta != 'tienda' else ''} {subcarpeta.capitalize()}{{% endblock %}}

{{% block content %}}
<div class="container">
    <h3>Lista de {subcarpeta}</h3>
    <p>Template en desarrollo. Aquí irá la lista de {subcarpeta}.</p>
</div>
{{% endblock %}}""")
                            elif 'detail.html' in archivo:
                                f.write(f"""{{% extends 'base.html' %}}

{{% block title %}}Detalle - TemucoSoft{{% endblock %}}

{{% block page_title %}}Detalle{{% endblock %}}

{{% block content %}}
<div class="container">
    <h3>Detalle</h3>
    <p>Template en desarrollo. Aquí irá el detalle.</p>
</div>
{{% endblock %}}""")
                            else:
                                f.write(f"""{{% extends 'base.html' %}}

{{% block title %}}{archivo.replace('.html', '').capitalize()} - TemucoSoft{{% endblock %}}

{{% block page_title %}}{archivo.replace('.html', '').capitalize()}{{% endblock %}}

{{% block content %}}
<div class="container">
    <h3>{archivo.replace('.html', '').capitalize()}</h3>
    <p>Template en desarrollo.</p>
</div>
{{% endblock %}}""")
                        print(f"  📄 Archivo creado: {ruta_archivo}")
                    else:
                        print(f"  ⚠️  Archivo ya existe: {ruta_archivo}")

if __name__ == "__main__":
    crear_estructura()
    print("\n✅ ¡Estructura de templates creada!")