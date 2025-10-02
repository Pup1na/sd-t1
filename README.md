# Sistema de Análisis de Calidad de Respuestas - Yahoo! Answers

Este proyecto implementa un sistema distribuido para analizar y comparar la calidad de respuestas generadas por un LLM versus respuestas humanas del dataset de Yahoo! Answers.

## 🏗️ Arquitectura del Sistema

El sistema está compuesto por 5 servicios principales:

1. **Traffic Generator**: Simula consultas de usuarios
2. **Cache Service**: Gestiona cache de respuestas frecuentes  
3. **LLM Service**: Integración con modelo de lenguaje (Gemini)
4. **Score Service**: Evalúa calidad de respuestas
5. **Storage Service**: Persistencia de datos

## 🚀 Configuración Inicial

### Prerequisitos

- Docker y Docker Compose
- Cuenta de Google AI Studio para API de Gemini
- Kaggle CLI (opcional, para dataset completo)

### Paso 1: Clonar y configurar

```bash
git clone <repo-url>
cd Tarea-1-Sistemas-distribuidos
```

### Paso 2: Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env y agregar tu GEMINI_API_KEY
```

### Paso 3: Obtener dataset

**Opción A: Dataset completo de Kaggle**
```bash
# Instalar kaggle CLI
pip install kaggle

# Configurar API key en ~/.kaggle/kaggle.json
# Luego ejecutar:
./download_data.sh
```

**Opción B: Usar dataset de ejemplo (para pruebas)**
```bash
# Ya incluido en data/sample_data.csv
```

### Paso 4: Inicializar base de datos y cargar datos

```bash
# Levantar solo PostgreSQL
docker-compose up -d postgres

# Cargar datos a la base de datos
docker-compose --profile tools run --rm data_loader

# Verificar carga de datos
docker-compose logs data_loader
```

### Paso 5: Ejecutar el sistema completo

```bash
docker-compose up --build
```

## 📊 Servicios y Puertos

- **Storage Service**: http://localhost:8001 - API de persistencia y acceso a datos
- **Cache Service**: http://localhost:8002 - Gestión de cache con Redis
- **Score Service**: http://localhost:8003 - Evaluación de calidad de respuestas
- **LLM Service**: http://localhost:8004 - Integración con Gemini API
- **Traffic Generator**: http://localhost:8005 - Generador de tráfico sintético
- **PostgreSQL**: localhost:5432 - Base de datos principal
- **Redis**: localhost:6379 - Cache en memoria

## 🔑 Configuración de Gemini API

1. Ir a [Google AI Studio](https://aistudio.google.com/)
2. Crear cuenta y obtener API key
3. Agregar la key al archivo `.env`:
   ```
   GEMINI_API_KEY=tu_api_key_aqui
   ```

## 📁 Estructura del Proyecto

```
├── services/
│   ├── data_loader/         # Carga inicial de datos CSV a BD
│   ├── traffic_generator/   # Generador de consultas  
│   ├── cache/              # Servicio de cache
│   ├── llm_service/        # Integración LLM
│   ├── score_service/      # Evaluación de calidad
│   └── storage/            # API de persistencia
├── data/                   # Datasets CSV
├── docs/                   # Documentación
├── docker-compose.yml      # Orquestación
└── download_data.sh        # Script descarga datos
```

## 🎯 Objetivos Cumplidos

### ✅ Todos los Servicios Implementados
- [x] **Data Loader**: Carga CSV → PostgreSQL con validación
- [x] **Storage Service**: API REST para acceso a datos y estadísticas  
- [x] **Cache Service**: Redis con políticas LRU/LFU/FIFO configurables
- [x] **LLM Service**: Integración completa con Gemini API
- [x] **Score Service**: Evaluación multi-métrica (cosine, BLEU, etc.)
- [x] **Traffic Generator**: 4 distribuciones (Poisson, Uniform, Exponential, Normal)
- [x] **Pipeline completo**: End-to-end funcional
- [x] **Dockerización**: Todos los servicios containerizados
- [x] **Script de pruebas**: Validación automática del sistema

## 🔄 Flujo de Datos Completo

1. **📥 Carga inicial**: `data_loader` → PostgreSQL (10K+ registros)
2. **🎯 Generación**: `traffic_generator` → selecciona preguntas de BD
3. **⚡ Cache**: `cache` → verifica Redis, políticas de evicción
4. **🤖 LLM**: `llm_service` → Gemini API para respuestas nuevas
5. **📊 Scoring**: `score_service` → evalúa calidad multi-métrica
6. **💾 Storage**: `storage` → persiste resultados y estadísticas

## � Uso del Sistema

### Inicialización Completa
```bash
# 1. Configurar variables de entorno
cp .env.example .env
# Agregar GEMINI_API_KEY

# 2. Levantar base de datos
docker-compose up -d postgres

# 3. Cargar datos
docker-compose --profile tools run --rm data_loader

# 4. Iniciar todos los servicios
docker-compose up --build

# 5. Probar el sistema
./test_system.sh
```

### Generar Tráfico
```bash
# Tráfico ligero
curl -X POST http://localhost:8005/start-traffic \
  -H "Content-Type: application/json" \
  -d '{"distribution":"uniform","rate":0.5,"duration":60}'

# Tráfico normal  
curl -X POST http://localhost:8005/start-traffic \
  -H "Content-Type: application/json" \
  -d '{"distribution":"poisson","rate":2.0,"duration":300}'
```

### Monitoreo en Tiempo Real
```bash
# Ver estadísticas básicas
curl http://localhost:8001/stats  # Storage
curl http://localhost:8002/cache/stats  # Cache
curl http://localhost:8005/stats  # Traffic

# Monitor especializado de cache hits
./monitor_cache.sh  # En terminal separada

# Verificación rápida de todos los servicios  
./quick_check.sh
```

## 📺 Logging en Terminal

Cuando ejecutes `docker-compose up`, verás logs detallados de:

- **📥 Carga de datos**: Progreso de descarga e importación CSV
- **🎯 Cache hits/misses**: Cada consulta muestra si fue hit o miss
- **🏆 Mejores respuestas**: Resalta respuestas con score > 0.7
- **🚦 Tráfico**: Progreso en tiempo real de consultas generadas
- **🤖 LLM**: Estado de generación de respuestas con Gemini

## 📚 Referencias

- [Dataset Yahoo! Answers](https://www.kaggle.com/datasets/jarupula/yahoo-answers-dataset)
- [Gemini API](https://ai.google.dev/gemini-api/docs)
- [Docker Compose](https://docs.docker.com/compose/)

---

**Entrega 1 - Sistemas Distribuidos 2025-1**
