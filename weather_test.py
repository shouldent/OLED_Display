import unicodedata

def get_simple_condition(raw_cond):
    # 1. Limpieza profunda: quita espacios, minúsculas y normaliza caracteres
    cond = raw_cond.lower().strip()
    
    # 2. Definimos las reglas en orden de prioridad
    # Si detecta 'thunder' en cualquier parte, gana. Si no, busca 'rain', etc.
    if 'thunder' in cond: return 'Thunder'
    if 'rain' in cond: return 'Rainy'
    if 'cloud' in cond or 'overcast' in cond: return 'Cloudy'
    if 'sun' in cond or 'clear' in cond: return 'Clear'
    if 'snow' in cond: return 'Snow'
    
    return 'N/A'

# Prueba rápida:
print(get_simple_condition("Patchy light rain")) # Debería imprimir 'Rainy'