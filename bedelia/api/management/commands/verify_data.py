"""
Script para verificar la integridad de los datos cargados.

Uso:
    python manage.py shell < bedelia/api/management/commands/verify_data.py
    
O ejecutar en Django shell:
    python manage.py shell
    >>> exec(open('bedelia/api/management/commands/verify_data.py').read())
"""

from api.models import Carrera, Curso, Previa, ItemPrevia, Posprevia

def print_header(title):
    """Imprimir encabezado."""
    print("\n" + "="*60)
    print(f"📊 {title}")
    print("="*60)

def verify_data():
    """Verificar la integridad de los datos."""
    
    print_header("RESUMEN DE DATOS")
    
    # Contar registros
    carreras_count = Carrera.objects.count()
    cursos_count = Curso.objects.count()
    previas_count = Previa.objects.count()
    items_count = ItemPrevia.objects.count()
    posprevias_count = Posprevia.objects.count()
    
    print(f"🎓 Carreras:        {carreras_count:,}")
    print(f"📚 Cursos:          {cursos_count:,}")
    print(f"🌳 Previas:         {previas_count:,}")
    print(f"📝 Items Previa:    {items_count:,}")
    print(f"🔗 Posprevias:      {posprevias_count:,}")
    
    # Verificar cursos con/sin previas
    print_header("ANÁLISIS DE PREVIAS")
    
    cursos_con_previas = Curso.objects.filter(previas__isnull=False).distinct().count()
    cursos_sin_previas = cursos_count - cursos_con_previas
    
    print(f"✅ Cursos con previas:  {cursos_con_previas:,} ({cursos_con_previas/cursos_count*100:.1f}%)")
    print(f"ℹ️  Cursos sin previas:  {cursos_sin_previas:,} ({cursos_sin_previas/cursos_count*100:.1f}%)")
    
    # Verificar previas raíz
    previas_raiz = Previa.objects.filter(padre__isnull=True).count()
    print(f"🌲 Previas raíz:        {previas_raiz:,}")
    
    # Distribución de tipos de previas
    print_header("DISTRIBUCIÓN DE TIPOS DE PREVIAS")
    
    for tipo, nombre in Previa.TIPO_NODO_CHOICES:
        count = Previa.objects.filter(tipo=tipo).count()
        print(f"{nombre:25s} ({tipo}): {count:,}")
    
    # Verificar cursos activos vs inactivos
    print_header("CURSOS ACTIVOS")
    
    cursos_activos = Curso.objects.filter(activo=True).count()
    cursos_inactivos = Curso.objects.filter(activo=False).count()
    
    print(f"✅ Activos:    {cursos_activos:,}")
    print(f"⛔ Inactivos:  {cursos_inactivos:,}")
    
    # Top carreras por número de cursos
    print_header("TOP 10 CARRERAS POR NÚMERO DE CURSOS")
    
    from django.db.models import Count
    
    top_carreras = Carrera.objects.annotate(
        num_cursos=Count('cursos')
    ).order_by('-num_cursos')[:10]
    
    for idx, carrera in enumerate(top_carreras, 1):
        print(f"{idx:2d}. {carrera.nombre[:40]:40s} {carrera.anio_plan or 'N/A':6s} - {carrera.num_cursos:3d} cursos")
    
    # Ejemplos de cursos
    print_header("EJEMPLOS DE CURSOS")
    
    ejemplos = Curso.objects.select_related().prefetch_related('carrera')[:5]
    
    for curso in ejemplos:
        carreras = ", ".join([c.nombre for c in curso.carrera.all()[:2]])
        print(f"📖 {curso.codigo_curso:8s} - {curso.nombre_curso[:40]:40s} ({curso.creditos} créditos)")
        print(f"   {carreras[:60]}")
        print()
    
    # Verificar integridad de previas
    print_header("VERIFICACIÓN DE INTEGRIDAD")
    
    # Verificar nodos LEAF sin items
    leaf_sin_items = Previa.objects.filter(tipo='LEAF', items__isnull=True).count()
    print(f"⚠️  Nodos LEAF sin items: {leaf_sin_items:,}")
    
    # Verificar nodos no-LEAF sin hijos
    nodos_sin_hijos = Previa.objects.exclude(tipo='LEAF').filter(hijos__isnull=True).count()
    print(f"⚠️  Nodos no-LEAF sin hijos: {nodos_sin_hijos:,}")
    
    # Verificar cursos sin carrera
    cursos_sin_carrera = Curso.objects.filter(carrera__isnull=True).count()
    print(f"⚠️  Cursos sin carrera: {cursos_sin_carrera:,}")
    
    # Estadísticas de modalidades
    print_header("MODALIDADES DE ITEMS")
    
    from django.db.models import Count
    modalidades = ItemPrevia.objects.values('modalidad').annotate(
        count=Count('id')
    ).order_by('-count')
    
    for mod in modalidades:
        print(f"{mod['modalidad']:15s}: {mod['count']:,}")
    
    print("\n" + "="*60)
    print("✅ Verificación completada")
    print("="*60 + "\n")

# Ejecutar verificación
if __name__ == '__main__':
    verify_data()
else:
    # Si se ejecuta desde shell, ejecutar automáticamente
    verify_data()

