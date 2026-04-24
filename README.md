# Scanner Global v3.3 — Hardened Candidate

Versión endurecida del scanner bursátil con enfoque en mantenibilidad, datos limpios, consenso multi-fuente y validación posterior.

## Qué corrige esta versión

- Código Python formateado y separado por módulos.
- `universe_global.csv` validado y estructurado una fila por activo.
- `requirements.txt` con versiones fijadas.
- Pruebas mínimas para indicadores, consenso y carga del universo.
- Endpoint `/api/status` reporta problemas de universo, fuentes activas y resumen.
- Motor de consenso bloquea veredictos fuertes cuando las fuentes contradicen demasiado.
- IA bajo demanda: solo se usa cuando seleccionas una señal y presionas **Analizar con IA**.
- Evaluación posterior de señales contra objetivo/stop.

## Instalación local

```powershell
python -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
python -m dotenv run -- python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Abre:

```text
http://127.0.0.1:8000
```

## Pruebas

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest
```

Opcional:

```powershell
python -m black backend tests
python -m ruff check backend tests
```

## Fuentes de datos

El sistema puede usar:

- Twelve Data
- Polygon
- Alpha Vantage
- yfinance como respaldo

Si no configuras API keys profesionales, funcionará con yfinance, pero la calidad del dato normalmente será baja/media por tener pocas fuentes.

## Variables clave

```env
TWELVE_DATA_API_KEY=
POLYGON_API_KEY=
ALPHA_VANTAGE_API_KEY=
ENABLE_YFINANCE=true
AI_PROVIDER=heuristic
OPENAI_API_KEY=
```

## Advertencia operativa

Este sistema no ejecuta órdenes. Para dinero real, valida siempre disponibilidad, precio, spread y liquidez en Kuspit/SIC antes de tomar cualquier decisión.
