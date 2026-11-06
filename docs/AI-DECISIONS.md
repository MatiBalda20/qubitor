# AI-DECISIONS.md

Log de auditoría de las decisiones técnicas y de arquitectura asistidas por IA durante el desarrollo de **Qubitor** (TPI — Desarrollo de Software Cloud, UTN FRLP, 2026). Cada entrada documenta el razonamiento detrás de código o diseño generado con un asistente de IA, y la validación/corrección humana aplicada antes de mergear a `main`.

Este archivo es obligatorio en la raíz del repositorio y es evidencia directa de integridad profesional y criterio técnico ante la cátedra: **toda incorporación de código o arquitectura generada por IA debe tener una entrada acá antes de abrir el PR correspondiente.**

## Cómo agregar una entrada

Copiar el bloque de abajo, completar los campos y agregarlo al final de este archivo (orden cronológico). Referenciar el número de PR cuando exista.

```markdown
### [AAAA-MM-DD] <Título corto de la decisión>

- **Problema abordado:** <descripción del desafío técnico>
- **Prompt / Herramienta utilizada:** <instrucción exacta enviada y asistente empleado>
- **Código / Arquitectura generada:** <resumen de lo que propuso la IA>
- **Validación y Corrección Humana:** <qué se identificó como alucinación, ineficiencia o riesgo de seguridad, y cómo se corrigió>
- **Responsable:** <integrante que revisó/mergeó>
- **PR:** #<número>
```

---

## Registro de decisiones

### [2026-09-27] Elección de arquitectura desacoplada de tres capas

- **Problema abordado:** Definir una infraestructura cloud-native para el MVP que minimice carga operativa (sin servidores propios) cumpliendo con el requisito de la cátedra de justificar cada componente por escalabilidad, costos y arquitectura.
- **Prompt / Herramienta utilizada:** Discusión asistida sobre trade-offs entre servicios gestionados de frontend (Cloudflare Pages vs. Vercel), backend (Render vs. AWS Lambda) y persistencia (Supabase vs. RDS/DynamoDB) para un equipo de 5 personas con foco académico y presupuesto free-tier.
- **Código / Arquitectura generada:** Propuesta de stack: React en Cloudflare Pages (frontend), FastAPI en Render (backend), Postgres administrado por Supabase con Row Level Security, Gemini API para evaluación de hallazgos, Clerk/Auth0 para autenticación.
- **Validación y Corrección Humana:** Se evaluó el riesgo de cold start en el plan free de Render (apagado tras 15 min de inactividad) — mitigado agregando un Cloudflare Worker con Cron Trigger que hace keep-alive cada 10 min a `/health`. Se descartó AWS Lambda como backend por la complejidad adicional de empaquetado de dependencias Python pesadas (motores de escaneo) frente al beneficio marginal para el volumen esperado del MVP académico.
- **Responsable:** Equipo en conjunto
- **PR:** #5

### [2026-10-27] Detector de criptografía post-cuántica para Python (pqc.py)

- **Problema abordado:** Detectar en repositorios Python el uso de algoritmos vulnerables a computación cuántica (RSA, DSA, ECDSA, ECDH y DH por el algoritmo de Shor; AES-128 por el de Grover) y registrar la criptografía segura (AES-256, SHA-2/SHA-3, BLAKE2, Argon2, ChaCha20-Poly1305) como inventario criptográfico (CBOM), respetando el contrato común de motores (`Finding`, `Severity`).
- **Prompt / Herramienta utilizada:** Claude Code (Claude Opus 5.5), trabajando de forma incremental bajo mi guía: yo definí el orden y el ritmo de los pasos, aprobé cada uno antes de su commit y pedí explicaciones línea por línea de cada pieza antes de avanzar. Decisiones mías durante el proceso: no commitear `base.py` (es del Módulo A; se usa una copia local hasta que se publique), exponer `scan_pqc` sin modificar `engines/crypto/__init__.py` hasta coordinarlo con el Módulo C, y dividir el inventario en pasos separados. Pasos: recorrido y parseo de archivos; RSA; ECDSA/ECDH; DH; AES según tamaño de clave; inventario de hashes, Argon2 y ChaCha20; soporte de pycryptodome, rsa y ecdsa, y DSA.
- **Código / Arquitectura generada:** `backend/app/engines/crypto/pqc.py` con la función pública `scan_pqc(repo_path)`. Analiza el código con el módulo `ast` en lugar de buscar texto: arma un mapa de imports para resolver el nombre completo de cada función llamada (soporta alias e imports directos, y distingue librerías con nombres iguales) y lo compara contra una tabla de reglas (`CALL_RULES`). Para AES, una función elige la severidad según el tamaño de clave escrito en la llamada. Reglas con prefijo `crypto.pqc.*` e inventario como `crypto.pqc.inventory.*` con severidad `info`. Librerías cubiertas: cryptography, pycryptodome, rsa, ecdsa, hashlib y argon2-cffi. 33 tests en `backend/tests/engines/test_pqc.py`, con casos positivos y negativos.
- **Validación y Corrección Humana:** Revisé cada paso antes de su commit y pedí la explicación línea por línea de cada función hasta entenderla (recorrido de archivos, mapa de imports, resolución de nombres y reglas). Ejecuté la suite de tests (33 tests, todos pasan) y verifiqué que fallen al quitar una regla. Validé que los casos negativos eviten falsos positivos: comentarios y textos que mencionan algoritmos, objetos propios con nombres como `rsa` y librerías con nombres iguales. Dejé MD5 y SHA-1 fuera del módulo a propósito porque corresponden a criptografía clásica (Módulo C). Limitaciones identificadas y aceptadas para el MVP: el análisis no sigue variables (por ejemplo, `parametros.generate_private_key()` no se detecta, aunque sí el `dh.generate_parameters` que lo origina); con `algorithms.AES(clave)` no se puede determinar el tamaño de la clave, así que se registra como inventario sin tamaño; todavía no se cubren X25519/Ed25519 ni la carga de claves con `RSA.import_key`. Pendiente coordinar con el Módulo C: RSA de menos de 2048 bits puede reportarse dos veces (como `high` en classic.py y como `medium` acá). En una revisión de seguridad que pedí antes de abrir el PR se encontraron y corrigieron dos problemas, verificados con archivos de prueba armados a propósito: (1) el detector seguía enlaces simbólicos, por lo que un repo malicioso podía hacerle leer archivos del servidor y filtrar su contenido en el reporte; ahora se saltean los enlaces y todo archivo que quede fuera del repo; (2) el `snippet` mostraba las claves escritas en el código (por ejemplo, `AES.new(b'clave')`), que se guardarían en la base y se enviarían a la IA, violando el contrato; ahora todo texto o bytes del snippet se reemplaza por `'***'` y el snippet se recorta a 200 caracteres. Se agregaron 4 tests que cubren estos casos.
- **Responsable:** Valentina Pértile de la Vega
- **PR:** #8

### [2026-11-02] Motor SCA de dependencias vulnerables con OSV (engines/sca)

- **Problema abordado:** Detectar dependencias con vulnerabilidades conocidas (CVE) en repositorios Python y JavaScript, informando gravedad, versión corregida y comando de actualización, como `Engine` del contrato común.
- **Prompt / Herramienta utilizada:** Claude Code (Claude Opus 5.5). Aprobé el plan de 6 pasos antes de empezar (un commit por paso) y las decisiones de diseño: no sumar librerías y usar la gravedad que calcula GitHub para el MVP.
- **Código / Arquitectura generada:** `backend/app/engines/sca/` en cuatro módulos: `manifests.py` (lee versiones exactas de `requirements*.txt`, `package.json` y `package-lock.json` v1/v2/v3, prefiriendo el lock), `osv.py` (cliente de la API de OSV con `urllib`: `querybatch` en lotes y detalle por ID), `findings.py` (convierte cada vulnerabilidad en `Finding` con CVE, CWE, gravedad, vector CVSS, versión corregida y comando `pip`/`npm`) y `engine.py` (`ScaEngine`: pide los detalles en paralelo, una vez por ID, y elimina las fallas repetidas con distinto ID usando los alias). 32 tests sin red con un OSV simulado, más un test opcional contra OSV real (`QUBITOR_TESTS_RED=1`).
- **Validación y Corrección Humana:** Revisé el plan antes de empezar y el resultado de cada paso. Ejecuté la suite de tests (32 sin red, todos pasan) y el test contra OSV real, que detecta CVE-2018-18074 en requests 2.19.0 y CVE-2019-10744 en lodash 4.17.4. Escaneé el repo de demo: 15 vulnerabilidades en unos 2 segundos, dentro del límite de 60 s del contrato. Durante el desarrollo se encontraron y corrigieron dos fallas, cada una con su test: un `package-lock.json` mal formado hacía fallar la lectura, y los campos en `null` de las entradas PYSEC de OSV rompían la conversión. Verifiqué que la misma falla publicada con dos IDs (GHSA y PYSEC) aparezca una sola vez y con la gravedad de GitHub, que la versión corregida se elija dentro de la rama instalada y comparando versiones como números (4.17.12 > 4.17.5), y que no se sigan enlaces a archivos fuera del repo. Limitaciones aceptadas para el MVP: solo se analizan versiones exactas (los rangos como `^4.17.4` se saltean si no hay lock); la gravedad se toma de GitHub y, si falta, se asume `medium` y queda marcada como desconocida; todavía no hay caché de OSV (se agrega con Cloudflare KV); si OSV no responde, el motor lanza `OsvError` para que el orquestador lo registre.
### [2026-11-02] Detector de criptografía post-cuántica para JavaScript (pqc.py)

- **Problema abordado:** Extender el detector post-cuántico a JavaScript y TypeScript (módulo `crypto` de Node.js), necesario para la falla plantada en `app/signing.js` del repo de demo.
- **Prompt / Herramienta utilizada:** Claude Code (Claude Opus 5.5), trabajando de forma incremental bajo mi guía: aprobé el enfoque y el commit, y pedí la explicación de cada pieza antes de avanzar.
- **Código / Arquitectura generada:** Detección con expresiones regulares (`JS_RULES`) sobre el código sin comentarios, reutilizando las mismas reglas que Python. Cubre `generateKeyPair(Sync)` (RSA, EC, DSA, DH), `createECDH`, `createDiffieHellman`, `createCipheriv` (AES por tamaño y ChaCha20) y `createHash` (inventario). Una función propia quita los comentarios `//` y `/* */` respetando los textos entre comillas y conservando los números de línea. El snippet se corta en el nombre del algoritmo para no incluir claves. Se generalizaron `_iter_files`, `_read_text` y `_make_finding` para los dos lenguajes. 9 tests nuevos (46 en total).
- **Validación y Corrección Humana:** Revisé la explicación de cada pieza antes del commit (patrones de `JS_RULES`, quitado de comentarios y armado del snippet). Ejecuté la suite de tests (46 tests, todos pasan) y escaneé el repo de demo `qubitor-demo-vulnerable`: la falla plantada en `app/signing.js` aparece como `crypto.pqc.ec-keygen` en la línea correcta. Validé los casos negativos: comentarios `//` y `/* */` que mencionan funciones criptográficas, URLs con `//` dentro de textos, tipos de clave ya post-cuánticos (`ml-dsa-65`) y MD5, que corresponde al Módulo C. Verifiqué que el snippet no incluya la clave pasada a `createCipheriv`. Decidí usar expresiones regulares en lugar de un parser de JavaScript para no sumar dependencias al scan-worker, aceptando estas limitaciones para el MVP: no se resuelve de dónde viene cada nombre (una función propia llamada `createECDH` también se detectaría), no se cubre WebCrypto (`crypto.subtle`), y como `crypto.sign` no indica el algoritmo, la firma ECDSA de la demo se reporta como generación de clave de curva elíptica (el riesgo es el mismo).
- **Responsable:** Valentina Pértile de la Vega
- **PR:** _pendiente_



### [2026-11-02] Contrato común entre motores (base.py)

- **Problema abordado:** Publicar la interfaz que comparten todos los motores (`Severity`, `Finding`, `Engine`) para que cada módulo desarrolle y pruebe su motor por separado y el orquestador los integre sin cambios. Los Módulos D (pqc y SCA) venían usando una copia local porque el archivo no estaba en `main`.
- **Prompt / Herramienta utilizada:** Claude Code (Claude Opus 5.5): pedí escribir `backend/app/engines/base.py` siguiendo al pie de la letra la sección 3 del plan de desarrollo, con tests.
- **Código / Arquitectura generada:** `base.py` con `Severity` (enum de texto: critical, high, medium, low, info), el dataclass `Finding` y la clase abstracta `Engine` con `scan(repo_path) -> list[Finding]`. 8 tests en `backend/tests/engines/test_base.py`: severidad desde texto y como texto, valores inválidos, campos opcionales por defecto, `metadata` independiente entre hallazgos y que un motor sin `scan` no se pueda instanciar.
- **Validación y Corrección Humana:** Verifiqué que los campos coincidan con el plan y con el uso que ya hacen `pqc.py` y el motor SCA (`cwe`, `cve`, `metadata`, `line`). Corrí la suite de pqc y la del SCA (desde su rama) contra este `base.py`: pasan todas salvo los tests de enlaces simbólicos, que fallan solo en Windows porque crear symlinks requiere permisos de administrador (no tiene relación con el contrato). Se dejó fuera del contrato el fingerprint y los pesos de severidad: son parte de la normalización y del Risk Score del orquestador.
- **Responsable:** Juan Ignacio Wilt
- **PR:** feat(engines): publicar el contrato común entre motores (base.py)

### [2026-11-02] Orquestador del escaneo (normalización, Risk Score y ejecución de motores)

- **Problema abordado:** Ejecutar todos los motores sobre un repo clonado sin que la falla de uno arruine el escaneo, unificar sus hallazgos sin duplicados y calcular el Risk Score y la nota A–F (etapas 2, 3 y 5 del pipeline).
- **Prompt / Herramienta utilizada:** Claude Code (Claude Opus 5.5), de a un paso por commit: (1) fingerprint y deduplicación, (2) Risk Score y nota, (3) ejecución en paralelo con timeout, (4) pipeline que une todo.
- **Código / Arquitectura generada:** `backend/app/orchestrator/`: `normalize.py` (fingerprint SHA-256 de motor + regla + archivo + línea; ante duplicados se queda el de mayor severidad), `risk.py` (pesos y umbrales de la sección 5 del plan; recibe solo las severidades que cuentan, así la API lo puede recalcular al marcar hallazgos como resueltos o falsos positivos), `runner.py` (`ThreadPoolExecutor` con un hilo por motor y límite de 70 s; los errores y timeouts quedan en un dict por motor) y `pipeline.py` (`analyze_repository(repo_path, engines)` → `ScanResult` con hallazgos por fingerprint, errores, score, nota y duración). 33 tests en `backend/tests/orchestrator/`.
- **Validación y Corrección Humana:** El orquestador recibe la lista de motores en lugar de importarlos, así se testea con motores falsos (que fallan, que se cuelgan, que tardan) y no depende de que estén mergeados. El fingerprint no incluye snippet ni severidad para que el mismo problema se reconozca entre escaneos aunque cambie el código vecino o la IA ajuste la severidad. Limitación aceptada: un hilo de Python no se puede cortar desde afuera, así que un motor colgado sigue corriendo después del timeout; se mitiga con los timeouts propios de cada motor (Bandit 50 s) y con que el scan-worker procesa un escaneo por proceso. Queda para el scan-worker: clonado (Módulo E), triage con IA entre la normalización y el score (Módulo E) y persistencia (modelos de Alvaro).
- **Responsable:** Juan Ignacio Wilt
- **PR:** feat(orchestrator): orquestador del escaneo
### [2026-11-02] Motor SAST con Bandit (SastEngine)

- **Problema abordado:** Detectar código inseguro en repos Python (eval/exec, SQL armada con strings, `shell=True`, pickle, YAML inseguro, TLS sin verificar, etc.) y devolverlo con el contrato común, para la vista «Código inseguro» y el Risk Score.
- **Prompt / Herramienta utilizada:** Claude Code (Claude Opus 5.5), de a un paso por commit: (1) ejecutar Bandit y leer su JSON, (2) convertir los resultados a `Finding`, (3) armar el motor y probarlo de punta a punta.
- **Código / Arquitectura generada:** `backend/app/engines/sast/`: `bandit.py` ejecuta `python -m bandit -r . -f json` como subproceso con el repo como directorio de trabajo (rutas relativas), límite de 50 s y exclusión de `node_modules`, `.venv`, `dist`, etc.; ante timeout, código de salida inesperado o salida inválida lanza `BanditError` para que el orquestador lo registre y siga. `findings.py` mapea severidad de Bandit a la escala unificada, sube a `high` eval, exec e inyección SQL, baja un nivel si la confianza es baja, agrega CWE y títulos en español. `engine.py` expone `SastEngine` (`name = "sast"`). Reglas con prefijo `sast.bandit.<id>`. 26 tests en `test_sast_bandit.py`, `test_sast_findings.py` y `test_sast_engine.py`.
- **Validación y Corrección Humana:** Revisé la salida real de Bandit antes de mapearla. Se detectó que la opción `-x node_modules` no excluía nada y se cambió por patrones `*/node_modules/*`, verificado con un test. Siguiendo lo que se encontró en el motor post-cuántico: se descartan enlaces simbólicos y archivos fuera del repo (un repo malicioso podría filtrar archivos del servidor en el snippet) y se enmascaran todos los textos del snippet, porque Bandit incluye líneas vecinas que pueden tener secretos; el costo es que en la SQL armada no se ve la consulta, pero sí la línea. En Windows Bandit usa `\` como separador: se normaliza para que funcione igual en Linux. Semgrep (JavaScript) queda pendiente hasta medir si entra en los 512 MB del plan free de Render. Pendiente: agregar `bandit` a las dependencias del scan-worker.
- **Responsable:** Juan Ignacio Wilt
- **PR:** feat(sast): motor SAST con Bandit

### [2026-11-06] Motor de Secretos (secrets/engine.py)

- **Problema abordado:** Detectar secretos hardcodeados mediante expresiones regulares (AWS, GitHub, Slack, etc.) y alta entropía de Shannon, garantizando que el valor expuesto no quede en texto plano dentro del hallazgo final ni se dupliquen puntajes.
- **Prompt / Herramienta utilizada:** Claude Opus, revisión asistida para resolver issues de un Code Review cruzado (enmascaramiento global por línea, deduplicación de tokens conocidos frente a entropía genérica y soporte de formatos sin comillas como `.env`).
- **Código / Arquitectura generada:** `SecretsEngine` lee archivos no excluidos línea por línea. Ejecuta 5 patrones específicos y un patrón genérico (`GENERIC_VAR_REGEX`) que soporta variables con guiones bajos y formatos de asignación diversos (`=`, `:`, con/sin comillas). Se utiliza una lista temporal de secretos por línea para aplicar el reemplazo `***` de forma global antes de instanciar los objetos `Finding`.
- **Validación y Corrección Humana:** Se identificó mediante pruebas que un token de GitHub asignado a una variable llamada `GITHUB_TOKEN` era reportado dos veces (por regex de GitHub y por entropía). Se corrigió agregando validación de deduplicación. Además, se ajustó el regex genérico para que soporte sintaxis de variables como `secret_value` y archivos sin comillas como `.env` o `.yaml`.
- **Responsable:** Alvaro Marini / Valentina Pértile de la Vega (Review)
- **PR:** #15

### [PLANTILLA — completar en próximas entradas]

- **Problema abordado:**
- **Prompt / Herramienta utilizada:**
- **Código / Arquitectura generada:**
- **Validación y Corrección Humana:**
- **Responsable:**
- **PR:** #
