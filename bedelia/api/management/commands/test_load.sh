#!/bin/bash
# Script de ayuda para testear el comando load_bedelia_data

echo "=========================================="
echo "🧪 Test del comando load_bedelia_data"
echo "=========================================="
echo ""

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Función para ejecutar comandos
run_test() {
    echo -e "${YELLOW}Ejecutando: $1${NC}"
    eval $1
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Éxito${NC}"
    else
        echo -e "${RED}❌ Error${NC}"
    fi
    echo ""
}

# 1. Dry run básico
echo "📋 Test 1: Dry run básico"
run_test "python manage.py load_bedelia_data --dry-run"

# 2. Dry run verbose
echo "📋 Test 2: Dry run verbose"
run_test "python manage.py load_bedelia_data --dry-run --verbose"

# 3. Verificar ayuda
echo "📋 Test 3: Verificar ayuda"
run_test "python manage.py load_bedelia_data --help"

echo "=========================================="
echo "✅ Tests completados"
echo "=========================================="
echo ""
echo "Para cargar datos reales:"
echo "  python manage.py load_bedelia_data --clear --verbose"
echo ""

