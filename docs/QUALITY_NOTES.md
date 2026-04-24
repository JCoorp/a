# Notas de calidad v3.3

## Cambios orientados a subir calidad técnica

1. CSV del universo limpio y validado por `backend/universe.py`.
2. Código Python legible, modular y preparado para Black/Ruff.
3. Pruebas mínimas para componentes críticos.
4. `requirements.txt` con versiones fijadas para evitar cambios inesperados.
5. Consenso multi-fuente con bloqueo si la divergencia supera el umbral configurado.
6. Evaluación posterior de señales activas contra stop/target.

## Pendientes para producción real

- Sustituir SQLite por PostgreSQL en cloud con volumen persistente.
- Agregar migraciones con Alembic.
- Ampliar backtesting por régimen de mercado.
- Integrar datos oficiales BMV/SIC o carga manual confiable de spreads Kuspit.
- Agregar pruebas de endpoints con base temporal.
- Agregar autenticación si se publica en internet.
