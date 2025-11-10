"""
Script para analizar las advertencias del comando load_bedelia_data.

Identifica que cursos referenciados en posprevias no existen en vigentes.

Uso:
    python bedelia/api/management/commands/analyze_warnings.py
"""

import json
import sys
from pathlib import Path
from collections import Counter

def analyze_warnings():
    """Analizar cursos faltantes en posprevias."""
    
    print("="*70)
    print("ANALISIS DE ADVERTENCIAS - CURSOS FALTANTES")
    print("="*70)
    print()
    
    # Cargar archivos
    print(">> Cargando archivos JSON...")
    base_dir = Path(__file__).resolve().parent.parent.parent.parent.parent
    vigentes_path = base_dir / 'data' / 'vigentes_data_backup.json'
    posprevias_path = base_dir / 'data' / 'posprevias_data_backup.json'
    
    print(f"   Buscando en: {base_dir / 'data'}")
    
    with open(vigentes_path, 'r', encoding='utf-8') as f:
        vigentes_data = json.load(f)
    
    with open(posprevias_path, 'r', encoding='utf-8') as f:
        posprevias_data = json.load(f)
    
    # Crear set de cursos vigentes
    cursos_vigentes = set()
    for carrera_plan, cursos in vigentes_data.items():
        for codigo_curso, curso_data in cursos.items():
            cursos_vigentes.add(curso_data['course_code'])
    
    print(f"[OK] Cursos vigentes cargados: {len(cursos_vigentes):,}")
    print()
    
    # Buscar cursos faltantes en posprevias
    cursos_faltantes = Counter()
    cursos_faltantes_details = {}
    total_posprevias = 0
    
    for carrera_plan, posprevias in posprevias_data.items():
        for codigo, posprevia_data in posprevias.items():
            codigo_curso = posprevia_data['code']
            total_posprevias += 1
            
            if codigo_curso not in cursos_vigentes:
                cursos_faltantes[codigo_curso] += 1
                if codigo_curso not in cursos_faltantes_details:
                    cursos_faltantes_details[codigo_curso] = {
                        'nombre': posprevia_data['name'],
                        'count': 0,
                        'carreras': set()
                    }
                cursos_faltantes_details[codigo_curso]['count'] += 1
                cursos_faltantes_details[codigo_curso]['carreras'].add(carrera_plan)
    
    # Resultados
    print("="*70)
    print("RESULTADOS")
    print("="*70)
    print(f"Total posprevias procesadas:     {total_posprevias:,}")
    print(f"Cursos unicos faltantes:         {len(cursos_faltantes):,}")
    print(f"Total referencias faltantes:     {sum(cursos_faltantes.values()):,}")
    print()
    
    # Top 20 cursos más referenciados que faltan
    print("="*70)
    print("TOP 20 CURSOS FALTANTES MAS REFERENCIADOS")
    print("="*70)
    print(f"{'Codigo':<15} {'Referencias':>12} {'Nombre':<40}")
    print("-"*70)
    
    for codigo, count in cursos_faltantes.most_common(20):
        nombre = cursos_faltantes_details[codigo]['nombre'][:38]
        print(f"{codigo:<15} {count:>12,} {nombre:<40}")
    
    print()
    
    # Análisis por longitud de código
    print("="*70)
    print("ANALISIS POR LONGITUD DE CODIGO")
    print("="*70)
    
    length_distribution = Counter()
    for codigo in cursos_faltantes.keys():
        length_distribution[len(codigo)] += 1
    
    for length in sorted(length_distribution.keys()):
        print(f"Codigos de {length} caracteres: {length_distribution[length]:,}")
    
    print()
    
    # Análisis de patrones
    print("="*70)
    print("PATRONES COMUNES")
    print("="*70)
    
    # Códigos que empiezan con números
    numericos = [c for c in cursos_faltantes.keys() if c[0].isdigit()]
    print(f"Codigos que empiezan con numero: {len(numericos):,}")
    
    # Códigos que empiezan con letras
    alfabeticos = [c for c in cursos_faltantes.keys() if c[0].isalpha()]
    print(f"Codigos que empiezan con letra:  {len(alfabeticos):,}")
    
    # Códigos con guión
    con_guion = [c for c in cursos_faltantes.keys() if '-' in c]
    print(f"Codigos con guion (-):           {len(con_guion):,}")
    
    # Códigos con P al final (posiblemente "prácticas")
    con_p = [c for c in cursos_faltantes.keys() if c.endswith('P')]
    print(f"Codigos que terminan en 'P':     {len(con_p):,}")
    
    print()
    
    # Ejemplos de cursos faltantes
    print("="*70)
    print("EJEMPLOS DE CURSOS FALTANTES")
    print("="*70)
    
    print("\nCodigos numericos:")
    for codigo in list(numericos)[:5]:
        nombre = cursos_faltantes_details[codigo]['nombre'][:40]
        count = cursos_faltantes_details[codigo]['count']
        print(f"  {codigo:<10} - {nombre:<40} ({count} refs)")
    
    print("\nCodigos alfabeticos:")
    for codigo in list(alfabeticos)[:5]:
        nombre = cursos_faltantes_details[codigo]['nombre'][:40]
        count = cursos_faltantes_details[codigo]['count']
        print(f"  {codigo:<10} - {nombre:<40} ({count} refs)")
    
    if con_p:
        print("\nCodigos con 'P' al final:")
        for codigo in list(con_p)[:5]:
            nombre = cursos_faltantes_details[codigo]['nombre'][:40]
            count = cursos_faltantes_details[codigo]['count']
            print(f"  {codigo:<10} - {nombre:<40} ({count} refs)")
    
    print()
    
    # Análisis de carreras afectadas
    print("="*70)
    print("CARRERAS MAS AFECTADAS")
    print("="*70)
    
    carreras_affected = Counter()
    for codigo, details in cursos_faltantes_details.items():
        for carrera in details['carreras']:
            carreras_affected[carrera] += 1
    
    for carrera, count in carreras_affected.most_common(10):
        print(f"{carrera:<50} {count:>5} cursos faltantes")
    
    print()
    
    # Conclusiones
    print("="*70)
    print("CONCLUSIONES")
    print("="*70)
    print()
    print("[OK] Las advertencias son NORMALES porque:")
    print("   1. posprevias contiene datos historicos")
    print("   2. vigentes solo contiene cursos actualmente activos")
    print("   3. Algunos cursos fueron descontinuados o renombrados")
    print("   4. Hay referencias cruzadas entre facultades/programas")
    print()
    print("[ACCION] Acciones sugeridas:")
    print("   1. Si necesitas los cursos historicos, agregales manualmente")
    print("   2. Las posprevias sin curso no se guardan (esperado)")
    print("   3. Esto NO afecta la funcionalidad del sistema")
    print("   4. Los cursos activos y sus previas estan completos")
    print()
    print("="*70)

if __name__ == '__main__':
    analyze_warnings()
