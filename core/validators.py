# core/validators.py
from django.core.exceptions import ValidationError
from django.utils import timezone
import re
from datetime import date

def validar_rut_chileno(value):
    """
    Valida RUT chileno con formato: 12.345.678-9 o 12345678-9
    """
    if not value:
        return
        
    rut = value.upper().replace('.', '').replace('-', '')
    
    if not re.match(r'^[0-9]+[0-9K]$', rut):
        raise ValidationError('Formato de RUT inválido')
    
    cuerpo = rut[:-1]
    dv = rut[-1]
    
    # Calcular dígito verificador
    suma = 0
    multiplicador = 2
    
    for c in reversed(cuerpo):
        suma += int(c) * multiplicador
        multiplicador = multiplicador + 1 if multiplicador < 7 else 2
    
    resto = 11 - (suma % 11)
    
    if resto == 11:
        dv_calculado = '0'
    elif resto == 10:
        dv_calculado = 'K'
    else:
        dv_calculado = str(resto)
    
    if dv_calculado != dv:
        raise ValidationError('RUT inválido - Dígito verificador incorrecto')

# --- ESTA ES LA FUNCIÓN QUE FALTABA ---
def validar_rut(value):
    """Alias para compatibilidad con el modelo que llama a 'validar_rut'"""
    return validar_rut_chileno(value)
# --------------------------------------

def validar_fecha_no_futura(value):
    """Valida que la fecha no sea futura"""
    if value > timezone.now().date():
        raise ValidationError('La fecha no puede ser futura')

def validar_fecha_inicio_antes_termino(inicio, termino):
    """Valida que la fecha de inicio sea antes que la de término"""
    if inicio >= termino:
        raise ValidationError('La fecha de inicio debe ser anterior a la fecha de término')

def validar_numero_positivo(value):
    """Valida que el número sea positivo"""
    if value < 0:
        raise ValidationError('El valor no puede ser negativo')