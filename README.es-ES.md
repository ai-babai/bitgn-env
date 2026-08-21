# bitgn-env

Entorno de trabajo para ejecuciones de BitGN, centrado en el solver nativo de Codex y en una evolución guiada por análisis.

[English version](./README.md) | Versión en español | [Русская версия](./README.ru.md)

## Clasificación de PAC

- Página del desafío: https://bitgn.com/challenge/PAC
- PAC es un benchmark en el que un agente ejecuta flujos de trabajo de inbox/ops dentro de espacios de trabajo restringidos y se evalúa según la exactitud de los resultados, las modificaciones de archivos y las referencias de contexto (grounding).

Estado público actual:

- Baseline de la ejecución ciega del día de la competición: `AGENTS.md` de <=100 líneas, 6.º puesto, `84/104` (84 puntos) en `pac1-prod`: https://bitgn.com/l/pac1-prod
- Configuración estable actual: límite predeterminado de 156 líneas (`LOCAL_RULES_MAX_AGENTS_LINES=156`) y `104/104` tareas resueltas.

## Enlaces rápidos

- Arquitectura: [`ARCHITECTURE.md`](./ARCHITECTURE.md)
- Política de evolución de reglas: [`RULES_EVOLUTION_PRINCIPLES.md`](./RULES_EVOLUTION_PRINCIPLES.md)
- Reglas locales activas: [`codex-agent-native/local-rules/AGENTS.md`](./codex-agent-native/local-rules/AGENTS.md)

## Cómo funciona (resumen)

Esta configuración casi parece un meme, pero funciona:

- Núcleo de políticas `AGENTS.md`: compacto y controlado por el operador (el baseline histórico usaba <=100 líneas; el límite predeterminado actual es 156).
- Codex CLI: ejecuta la sesión de trabajo real.
- Wrapper de herramientas: expone a Codex únicamente las herramientas relevantes para PAC.
- Modelo: `gpt-5.3-codex`, el solver predeterminado actual.

En resumen: `archivo de políticas de 100 líneas -> sesión de Codex -> herramientas restringidas -> resultado evaluado`.

Baseline histórico:

- La configuración original con un `AGENTS.md` de <=100 líneas alcanzó el 6.º puesto con `84/104` tareas resueltas en `pac1-prod`: https://bitgn.com/l/pac1-prod
- El ciclo actual alcanzó `104/104` mejorando la calidad de las reglas y la orquestación de las ejecuciones, no mediante respuestas específicas codificadas para cada tarea.

## Arquitectura (visión general)

Este repositorio utiliza un ciclo de dos módulos:

- `codex-agent-native`: ejecuta las tareas del benchmark y genera todos los artefactos de cada tarea.
- `codex-agent-analytics`: lee los artefactos de las ejecuciones nativas, identifica patrones de fallo, propone actualizaciones de reglas y despliega nuevas versiones.

La idea principal es mantener separadas la resolución durante la ejecución y el análisis posterior:

- el runner nativo está optimizado para una ejecución fiable y trazable;
- el runner de análisis está optimizado para una evolución controlada y auditable de las políticas.

## Componentes principales

- `run-codex-native.sh`: wrapper de entrada para ejecuciones nativas (sandbox/pac1, paralelismo, modelo y opciones de la clasificación).
- `codex-agent-native/runner.py`: orquesta `start_playground/start_trial`, la creación de un espacio de trabajo por tarea, la sesión de Codex, la evaluación y la escritura del manifiesto.
- `codex-agent-native/runtime_tools.py`: gateway de herramientas expuesto a Codex durante la resolución.
- `codex-agent-native/local-rules/AGENTS.md`: política local activa que utiliza el solver nativo.
- `run-codex-analytics.sh`: wrapper de entrada para los flujos de trabajo `analyze | apply | deploy`.
- `codex-agent-analytics/cli.py`: plano de control del pipeline de análisis.
- `codex-agent-analytics/rules_versions/`: snapshots versionados de las políticas (`rvXXXX`).

## Ciclo de evolución (visión general)

Una iteración típica:

1. **Resolver**: ejecutar el runner nativo en el alcance elegido (una tarea, un grupo de riesgo o el benchmark completo).
2. **Analizar**: revisar las tareas fallidas y generar propuestas.
3. **Aplicar**: aplicar una propuesta aprobada en una nueva versión de las reglas.
4. **Desplegar**: copiar la versión elegida a `codex-agent-native/local-rules/AGENTS.md`.
5. **Validar**: volver a ejecutar las tareas objetivo y el grupo de riesgo; si todo está correcto, ejecutar el smoke test completo y, opcionalmente, una ejecución para la clasificación.

Este ciclo permite iteraciones locales rápidas con un radio de impacto controlado antes de enviar resultados a la clasificación.

## Comandos rápidos

### Ejecución nativa

```bash
cd bitgn-env

# Una tarea de PAC1
./run-codex-native.sh --env pac1 t01

# PAC1 completo (resuelve automáticamente todas las tareas del benchmark)
./run-codex-native.sh --env pac1 --all -p 5

# PAC1 completo (lista explícita de tareas)
./run-codex-native.sh --env pac1 -p 5 t{01..43}

# PAC1 completo con orden personalizado y fail-fast
./run-codex-native.sh --env pac1 --fail-fast -p 9 t03 t17 t28 t01 t02
```

Notas:

- El runner nativo ejecuta las tareas exactamente en el orden indicado en la CLI.
- `--fail-fast` deja de programar nuevas tareas después del primer fallo; si `parallelism > 1`, las tareas que ya están en ejecución terminan normalmente.

### Selección del backend (Spark / OmniRoute)

```bash
# Backend Spark/Codex directo (usa el inicio de sesión de ChatGPT o el perfil de Codex seleccionado)
CODEX_BACKEND=spark ./run-codex-native.sh --env pac1 t01

# Spark con un perfil explícito (si está configurado en ~/.codex/config.toml)
CODEX_BACKEND=spark CODEX_PROFILE=<your-spark-profile> ./run-codex-native.sh --env pac1 t01

# Backend OmniRoute (predeterminado actualmente)
CODEX_BACKEND=omniroute ./run-codex-native.sh --env pac1 t01
```

Notas:

- `CODEX_PROFILE` es opcional; si se define, se pasa a `codex exec --profile <name>`.
- Si `CODEX_BACKEND=spark` y `CODEX_PROFILE` está vacío, los wrappers fuerzan el proveedor directo mediante `-c model_provider=openai`.
- La clave de OmniRoute solo es necesaria cuando `CODEX_BACKEND=omniroute`.

### Modo smoke (sin clasificación)

```bash
BITGN_API_KEY='' BITGN_API_KEY_FILE='/tmp/bitgn-no-key' \
BITGN_RUN_NAME='[@skifmax]-[codex]-[chiki-banboni]-[smoke]' \
./run-codex-native.sh --env pac1 -p 5 t{01..43}
```

### Modo de clasificación

```bash
BITGN_RUN_NAME='[@skifmax]-[codex]-[chiki-banboni]-[xNNN]' \
./run-codex-native.sh --env pac1 --all -p 5
```

Consulta la clasificación y las comparaciones entre ejecuciones en https://bitgn.com/challenge/PAC.

### Evolución mediante análisis

```bash
# Analizar una tarea fallida de una ejecución local
./run-codex-analytics.sh analyze --env pac1 --run-id <local_run_id> -p 1 --focus-task t36 t36

# Aplicar una propuesta seleccionada de una versión de reglas existente
./run-codex-analytics.sh apply --proposal-id prop-001 --from-version rv0038

# Desplegar la versión resultante en las reglas locales del runner nativo
./run-codex-analytics.sh deploy --rules-version rv0039 --yes
```

## Artefactos y observabilidad

- Raíz de las ejecuciones nativas: `codex-agent-native/runs/<local_run_id>/`
- Espacio de trabajo por tarea: `codex-agent-native/runs/<local_run_id>/<task_id>/attempt_<timestamp>_<id>/`
- Manifiesto de la ejecución: `codex-agent-native/runs/<local_run_id>/run_manifest.jsonl`
- Puntuación por tarea: `.../score.json` (éxito/fallo, detalles de puntuación, tokens y pasos)

Artefactos del análisis:

- resumen del análisis: `codex-agent-analytics/analysis/aXXXX.json`
- informe: `codex-agent-analytics/reports/rXXXX.md`
- propuestas: `codex-agent-analytics/proposals/rules/<rv>/prop-XXX.md`
- informes de aplicación/despliegue: `codex-agent-analytics/applies/aXXXX.md`, `codex-agent-analytics/deploy/dXXXX.md`

## Notas de configuración

- Selector de backend: `CODEX_BACKEND=omniroute|spark` (predeterminado: `omniroute`).
- Perfil opcional para Codex CLI: `CODEX_PROFILE=<profile-name>`.
- Clave de OmniRoute para los flujos de Codex: `OMNIROUTE_API_KEY` (solo es necesaria para `CODEX_BACKEND=omniroute`).
- Orden de resolución de la clave en el wrapper:
  1. Variable de entorno `OMNIROUTE_API_KEY`
  2. `BITGN_OMNIROUTE_KEY_FILE`
  3. `$HOME/.codex/omniroute-api-key`
- Modelo del runner nativo: `CODEX_MODEL` (predeterminado: `gpt-5.3-codex`).
- Paralelismo del runner nativo: `-p` / `--parallelism` o `NATIVE_PARALLELISM`.
- Límite de líneas de las reglas locales: `LOCAL_RULES_MAX_AGENTS_LINES` (predeterminado: `156`).

## Documentación relacionada

- Detalles del runner nativo: [`codex-agent-native/README.md`](./codex-agent-native/README.md)
- Detalles del análisis: [`codex-agent-analytics/README.md`](./codex-agent-analytics/README.md)
- Descripción detallada de la arquitectura: [`ARCHITECTURE.md`](./ARCHITECTURE.md)
- Diseño de reglas y política de evolución: [`RULES_EVOLUTION_PRINCIPLES.md`](./RULES_EVOLUTION_PRINCIPLES.md)
- Reglas locales activas: [`codex-agent-native/local-rules/AGENTS.md`](./codex-agent-native/local-rules/AGENTS.md)
- Dashboard de ejecuciones de BitGN (preview): https://preview.mipopkov.com/bitgn-dash/
- Repositorio del dashboard de BitGN: https://github.com/ai-babai/bitgn-dash
- Referencia del proveedor: [`OmniRoute`](https://github.com/diegosouzapw/OmniRoute/), el proveedor de backend utilizado habitualmente para `CODEX_BACKEND=omniroute`
- Navegación y reglas del nivel raíz en esta máquina: [`AGENTS.md`](./AGENTS.md)

## Contacto

- Maksim Popkov
- Telegram: `@skifmax`
- Email: `contact.popkov@yandex.com`
- Sitios: https://mipopkov.com, https://mipopkov.ru
- LinkedIn: https://www.linkedin.com/in/maksim-popkov/
