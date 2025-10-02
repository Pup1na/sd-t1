#!/bin/bash

echo "🔽 Descargando dataset de Yahoo! Answers..."

mkdir -p data

if ! command -v kaggle &> /dev/null; then
    echo "❌ Error: Kaggle CLI no está instalado."
    echo "📦 Instálalo con: pip install kaggle"
    echo "🔑 Luego configura tu API key en ~/.kaggle/kaggle.json"
    exit 1
fi

if [ ! -f ~/.kaggle/kaggle.json ]; then
    echo "❌ Error: Kaggle API no está configurada."
    echo "🔑 Configura tu API key en ~/.kaggle/kaggle.json"
    echo "📖 Más info: https://github.com/Kaggle/kaggle-api#api-credentials"
    exit 1
fi

cd data
kaggle datasets download -d jarupula/yahoo-answers-dataset

if [ $? -eq 0 ]; then
    echo "✅ Dataset descargado exitosamente"
    
    echo "📦 Extrayendo archivos..."
    unzip -o yahoo-answers-dataset.zip
    
    if [ -f "train.csv" ] && [ -f "test.csv" ]; then
        echo "✅ Archivos extraídos correctamente:"
        echo "   📄 train.csv: $(wc -l < train.csv) líneas"
        echo "   📄 test.csv: $(wc -l < test.csv) líneas"
        
        rm yahoo-answers-dataset.zip
        
        echo "🎉 ¡Dataset listo para usar!"
        echo ""
        echo "📋 Próximos pasos:"
        echo "1. Configurar variables de entorno: cp .env.example .env"
        echo "2. Agregar tu GEMINI_API_KEY al archivo .env"
        echo "3. Cargar datos a la base de datos: docker-compose --profile tools run --rm data_loader"
        echo "4. Iniciar el sistema: docker-compose up --build"
    else
        echo "❌ Error: No se encontraron los archivos esperados"
        exit 1
    fi
else
    echo "❌ Error descargando el dataset"
    exit 1
fi
