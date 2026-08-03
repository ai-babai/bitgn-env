

# bitgn-env

Entorno de trabajo para ejecuciones de BitGN con enfoque en el solver nativo de Codex y una evolución impulsada por analítica.

Español | [Versión en ruso](./README.ru.md)

## Tabla de clasificación PAC

- Página del desafío: https://bitgn.com/challenge/PAC
- PAC es un benchmark donde el agente ejecuta flujos de trabajo de inbox/ops dentro de espacios de tarea restringidos y se evalúa según la exactitud de los resultados, mutaciones de archivos y referencias de contexto (grounding).

Estado público actual:

- Línea base de ejecución ciega del día de la competición: `AGENTS.md` de <=100 líneas, 6.º puesto, `84/104` (84 puntos) en `pac1-prod`: https://bitgn.com/l/pac1-prod
- Configuración actual estabilizada: límite predeterminado de 156 líneas (`LOCAL_RULES_MAX_AGENTS_LINES=156`) y `104/104` resueltos.

## Enlaces rápidos

- Arquitectura: [`ARCHITECTURE.md`](./ARCHITECTURE.md)
- Política de evolución de reglas: [`RULES_EVOLUTION_PRINCIPLES.md`](./RULES_EVOLUTION_PRINCIPLES.md)
- Reglas locales activas: [`codex-agent-native/local-rules/AGENTS.md`](./codex-agent-native/local-rules/AGENTS.md)

## Cómo funciona (resumen)

Esta configuración es casi un meme, pero funciona:

- Cerebro de políticas `AGENTS.md`: compacto y controlado por el operador (la línea base histórica usaba <=100 líneas; el límite nativo predeterminado actual es 156).
- Codex CLI: ejecuta la sesión real de la tarea.
- Wrapper de herramientas: expone únicamente las herramientas relevantes para PAC a Codex.
- Modelo: `gpt-5.3-codex` - solver predeterminado actual.

En resumen: `archivo de políticas de 100 líneas -> sesión de Codex -> herramientas restringidas -> resultado evaluado`.

Línea base histórica:

- La configuración original de `AGENTS.md` de <=100 líneas alcanzó el 6.º puesto con `84/104` resueltos en `pac1-prod`: https://bitgn.com/l/pac1-prod
- El ciclo actual alcanzó `104/104` mejorando la calidad de las reglas y la orquestación de las ejecuciones (no mediante la codificación estática de respuestas específicas para cada tarea).

## Arquitectura (nivel alto)

Este repositorio utiliza un ciclo de dos módulos:

- `codex-agent-native`: ejecuta tareas del benchmark y genera todos los artefactos de la tarea.
- `codex-agent-analytics`: lee los artefactos nativos, identifica patrones de fallo, propone actualizaciones de reglas y despliega nuevas versiones de reglas.

La idea clave es mantener separada la resolución en tiempo de ejecución y el análisis posterior:

- el ejecutor nativo optimiza para una ejecución confiable y trazable,
- el ejecutor de analítica optimiza para una evolución de políticas controlada y auditable.

## Componentes principales

- `run-codex-native.sh`: wrapper de entrada para ejecuciones nativas (sandbox/pac1, paralelismo, modelo, banderas de tabla de clasificación).
- `codex-agent-native/runner.py`: orquesta `start_playground/start_trial`, la creación del espacio de trabajo por tarea, la ejecución de la sesión de Codex, la evaluación y la escritura del manifiesto.
- `codex-agent-native/runtime_tools.py`: puerta de enlace de herramientas expuesta a Codex durante la resolución.
- `codex-agent-native/local-rules/AGENTS.md`: política local activa utilizada por el solver nativo.
- `run-codex-analytics.sh`: wrapper de entrada para flujos de trabajo `analyze | apply | deploy`.
- `codex-agent-analytics/cli.py`: plano de control del pipeline de analítica.
- `codex-agent-analytics/rules_versions/`: instantáneas de políticas versionadas (`rvXXXX`).

## Ciclo de evolución (nivel alto)

Iteración típica:

1. **Resolver**: ejecutar el nativo en el alcance seleccionado (tarea única, clúster de riesgo o benchmark completo).
2. **Analizar**: inspeccionar tareas fallidas y generar propuestas.
3. **Aplicar**: aplicar una propuesta aprobada en una nueva versión de reglas.
4. **Desplegar**: copiar la versión de reglas seleccionada a `codex-agent-native/local-rules/AGENTS.md`.
5. **Validar**: volver a ejecutar tareas objetivo y clúster de riesgo; si pasan, ejecutar prueba rápida (smoke) completa; luego ejecución opcional en la tabla de clasificación.

Este ciclo permite iteraciones locales rápidas con un radio de impacto controlado antes de los envíos a la tabla de clasificación.

## Comandos rápidos

### Ejecución nativa

```bash
cd bitgn-env

# single PAC1 task
./run-codex-native.sh --env pac1 t01

# full PAC1 (auto-resolve all tasks from benchmark)
./run-codex-native.sh --env pac1 --all -p 5

# full PAC1 (explicit task list)
./run-codex-native.sh --env pac1 -p 5 t{01..43}

# full PAC1 with custom order + fail-fast
./run-codex-native.sh --env pac1 --fail-fast -p 9 t03 t17 t28 t01 t02
```

Notas:

- El ejecutor nativo ejecuta las tareas en el orden exacto que se pasa en la CLI.
- `--fail-fast` detiene la programación después de la primera tarea fallida (las tareas en ejecución terminan cuando paralelismo > 1).

### Selección de backend (Spark / OmniRoute)

```bash
# Spark/direct Codex backend (uses ChatGPT login or selected codex profile)
CODEX_BACKEND=spark ./run-codex-native.sh --env pac1 t01

# Spark + explicit profile (if you configured one in ~/.codex/config.toml)
CODEX_BACKEND=spark CODEX_PROFILE=<your-spark-profile> ./run-codex-native.sh --env pac1 t01

# OmniRoute backend (current default)
CODEX_BACKEND=omniroute ./run-codex-native.sh --env pac1 t01
```

Notas:

- `CODEX_PROFILE` es opcional; si se establece, se pasa a `codex exec --profile <nombre>`.
- Si `CODEX_BACKEND=spark` y `CODEX_PROFILE` está vacío, los wrappers fuerzan el proveedor directo mediante `-c model_provider=openai`.
- La clave de OmniRoute es requerida únicamente cuando `CODEX_BACKEND=omniroute`.

### Modo smoke test (sin tabla de clasificación)

```bash
BITGN_API_KEY='' BITGN_API_KEY_FILE='/tmp/bitgn-no-key' \
BITGN_RUN_NAME='[@skifmax]-[codex]-[chiki-banboni]-[smoke]' \
./run-codex-native.sh --env pac1 -p 5 t{01..43}
```

### Modo tabla de clasificación

```bash
BITGN_RUN_NAME='[@skifmax]-[codex]-[chiki-banboni]-[xNNN]' \
./run-codex-native.sh --env pac1 --all -p 5
```

Consulta el ranking de la tabla de clasificación y las comparaciones de ejecuciones en https://bitgn.com/challenge/PAC.

### Evolución de analítica

```bash
# analyze one failed task from a local run
./run-codex-analytics.sh analyze --env pac1 --run-id <local_run_id> -p 1 --focus-task t36 t36

# apply selected proposal from an existing rules version
./run-codex-analytics.sh apply --proposal-id prop-001 --from-version rv0038

# deploy resulting rules version to native local-rules
./run-codex-analytics.sh deploy --rules-version rv0039 --yes
```

## Artefactos y observabilidad

- Raíz de ejecución nativa: `codex-agent-native/runs/<local_run_id>/`
- Espacio de trabajo por tarea: `codex-agent-native/runs/<local_run_id>/<task_id>/attempt_<timestamp>_<id>/`
- Manifiesto de ejecución: `codex-agent-native/runs/<local_run_id>/run_manifest.jsonl`
- Puntuación por tarea: `.../score.json` (éxito/fallo, detalles de puntuación, tokens, pasos)

Artefactos de analítica:

- resumen del análisis: `codex-agent-analytics/analysis/aXXXX.json`
- informe: `codex-agent-analytics/reports/rXXXX.md`
- propuestas: `codex-agent-analytics/proposals/rules/<rv>/prop-XXX.md`
- informes de apply/deploy: `codex-agent-analytics/applies/aXXXX.md`, `codex-agent-analytics/deploy/dXXXX.md`

## Notas de configuración

- Cambio de backend: `CODEX_BACKEND=omniroute|spark` (predeterminado: `omniroute`).
- Anulación opcional de perfil para Codex CLI: `CODEX_PROFILE=<nombre-perfil>`.
- Clave de OmniRoute para flujos de Codex: `OMNIROUTE_API_KEY` (requerida solo para `CODEX_BACKEND=omniroute`).
- Orden de resolución de claves del wrapper:
  1. `OMNIROUTE_API_KEY` env
  2. `BITGN_OMNIROUTE_KEY_FILE`
  3. `$HOME/.codex/omniroute-api-key`
- Anulación de modelo nativo: `CODEX_MODEL` (predeterminado `gpt-5.3-codex`).
- Paralelismo nativo: `-p` / `--parallelism` o `NATIVE_PARALLELISM`.
- Límite de líneas para reglas locales nativas: `LOCAL_RULES_MAX_AGENTS_LINES` (predeterminado `156`).

## Documentación relacionada

- Detalles nativos: [`codex-agent-native/README.md`](./codex-agent-native/README.md)
- Detalles de analítica: [`codex-agent-analytics/README.md`](./codex-agent-analytics/README.md)
- Análisis profundo de arquitectura: [`ARCHITECTURE.md`](./ARCHITECTURE.md)
- Diseño de reglas y política de evolución: [`RULES_EVOLUTION_PRINCIPLES.md`](./RULES_EVOLUTION_PRINCIPLES.md)
- Reglas locales activas: [`codex-agent-native/local-rules/AGENTS.md`](./codex-agent-native/local-rules/AGENTS.md)
- Panel de ejecuciones de BitGN (vista previa): https://preview.mipopkov.com/bitgn-dash/
- Repo del panel de BitGN: https://github.com/ai-babai/bitgn-dash
- Referencia del proveedor: [`OmniRoute`](https://github.com/diegosouzapw/OmniRoute/) — proveedor de backend comúnmente utilizado para `CODEX_BACKEND=omniroute`
- Navegación/reglas de nivel raíz en esta máquina: [`AGENTS.md`](./AGENTS.md)

## Contacto

- Maksim Popkov
- Telegram: `@skifmax`
- Email: `contact.popkov@yandex.com`
- Sitios: https://mipopkov.com, https://mipopkov.ru
- LinkedIn: https://www.linkedin.com/in/maksim-popkov/
