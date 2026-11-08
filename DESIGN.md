---
name: Qubitor
description: Auditoría continua de seguridad; la nota del repositorio como un cartel oficial de inspección.
colors:
  paper: "oklch(0.968 0.007 250)"
  sheet: "oklch(0.995 0.002 250)"
  ink: "oklch(0.23 0.035 262)"
  ink-2: "oklch(0.4 0.03 262)"
  ink-3: "oklch(0.5 0.025 262)"
  rule: "oklch(0.88 0.012 255)"
  rule-2: "oklch(0.8 0.018 255)"
  civic: "oklch(0.37 0.13 262)"
  civic-deep: "oklch(0.3 0.11 262)"
  civic-ink: "oklch(0.97 0.01 262)"
  civic-muted: "oklch(0.84 0.04 262)"
  civic-soft: "oklch(0.94 0.025 262)"
  stamp: "oklch(0.44 0.16 278)"
  sev-critical: "oklch(0.53 0.2 27)"
  sev-critical-soft: "oklch(0.95 0.03 27)"
  sev-high: "oklch(0.6 0.17 48)"
  sev-high-ink: "oklch(0.48 0.14 48)"
  sev-high-soft: "oklch(0.955 0.035 60)"
  sev-medium: "oklch(0.77 0.15 85)"
  sev-medium-ink: "oklch(0.47 0.1 75)"
  sev-medium-soft: "oklch(0.965 0.04 90)"
  sev-low: "oklch(0.6 0.08 235)"
  sev-low-ink: "oklch(0.45 0.08 240)"
  sev-low-soft: "oklch(0.95 0.02 235)"
  sev-info: "oklch(0.7 0.012 262)"
  sev-info-ink: "oklch(0.45 0.02 262)"
  sev-info-soft: "oklch(0.945 0.006 262)"
  ok: "oklch(0.5 0.12 155)"
  ok-soft: "oklch(0.95 0.03 155)"
typography:
  display:
    fontFamily: "Barlow Condensed, Public Sans Variable, ui-sans-serif, sans-serif"
    fontSize: "9rem"
    fontWeight: 700
    lineHeight: 1
  headline:
    fontFamily: "Barlow Condensed, Public Sans Variable, ui-sans-serif, sans-serif"
    fontSize: "3rem"
    fontWeight: 600
    lineHeight: 1
    fontFeature: "\"tnum\""
  figure:
    fontFamily: "Barlow Condensed, Public Sans Variable, ui-sans-serif, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 600
    lineHeight: 1
    fontFeature: "\"tnum\""
  page-title:
    fontFamily: "Public Sans Variable, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.75rem"
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "-0.01em"
  title:
    fontFamily: "Public Sans Variable, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 600
    lineHeight: 1.5
  body:
    fontFamily: "Public Sans Variable, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.5
  body-sm:
    fontFamily: "Public Sans Variable, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.43
  label:
    fontFamily: "Public Sans Variable, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.6875rem"
    fontWeight: 600
    letterSpacing: "0.06em"
  mono:
    fontFamily: "JetBrains Mono Variable, ui-monospace, Cascadia Code, monospace"
    fontSize: "0.8125rem"
    fontWeight: 400
    lineHeight: 1.5
rounded:
  xs: "2px"
  sm: "4px"
  full: "9999px"
spacing:
  gutter-mobile: "16px"
  gutter: "32px"
  stack: "20px"
  sheet-x: "20px"
  sheet-header-y: "14px"
  row-y: "14px"
components:
  button-primary:
    backgroundColor: "{colors.civic}"
    textColor: "{colors.civic-ink}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.sm}"
    padding: "0 16px"
    height: "40px"
  button-primary-hover:
    backgroundColor: "{colors.civic-deep}"
  button-secondary:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.sm}"
    padding: "0 12px"
    height: "36px"
  button-secondary-hover:
    backgroundColor: "{colors.civic-soft}"
  tab:
    textColor: "{colors.ink-2}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.sm}"
    padding: "0 12px"
    height: "36px"
  tab-active:
    backgroundColor: "{colors.civic}"
    textColor: "{colors.civic-ink}"
  chip-filter:
    textColor: "{colors.ink-2}"
    rounded: "{rounded.sm}"
    padding: "0 10px"
    height: "32px"
  chip-filter-active:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.sheet}"
  input:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.sm}"
    height: "36px"
  sheet:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
  notice-band:
    backgroundColor: "{colors.civic}"
    textColor: "{colors.civic-ink}"
    padding: "10px 20px"
  nav-rail:
    backgroundColor: "{colors.civic}"
    textColor: "{colors.civic-ink}"
    width: "15.5rem"
  nav-item-active:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.civic}"
    rounded: "{rounded.sm}"
    height: "40px"
  severity-badge-critical:
    backgroundColor: "{colors.sev-critical}"
    textColor: "{colors.sheet}"
    typography: "{typography.label}"
    rounded: "{rounded.xs}"
    height: "24px"
  severity-badge-high:
    backgroundColor: "{colors.sev-high-soft}"
    textColor: "{colors.sev-high-ink}"
    rounded: "{rounded.xs}"
    height: "24px"
  severity-badge-medium:
    backgroundColor: "{colors.sev-medium-soft}"
    textColor: "{colors.sev-medium-ink}"
    rounded: "{rounded.xs}"
    height: "24px"
  severity-badge-low:
    backgroundColor: "{colors.sev-low-soft}"
    textColor: "{colors.sev-low-ink}"
    rounded: "{rounded.xs}"
    height: "24px"
  severity-badge-info:
    backgroundColor: "{colors.sev-info-soft}"
    textColor: "{colors.sev-info-ink}"
    rounded: "{rounded.xs}"
    height: "24px"
  toast:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.sheet}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.sm}"
    padding: "10px 8px 10px 16px"
---

# Design System: Qubitor

## Overview

**Creative North Star: "El cartel oficial de inspección"**

Qubitor se ve como la papelería de una oficina de inspección: papel de formulario frío, tinta institucional azul, campos rotulados y sellos. La nota A–F no es una métrica de SaaS sino el certificado que se pega en la vidriera: una letra grande dentro de un recuadro de doble filete, con el puntaje, la penalización y un sello fechado. Todo lo demás (tablas, fichas de hallazgo, progreso del escaneo) es el resto del expediente: hojas blancas sobre papel gris azulado, filas separadas por filetes finos, cifras tabulares.

La densidad es de herramienta profesional: mucha información por pantalla, ordenada por severidad, sin decoración que compita con los hallazgos. El color se gasta en dos lugares: la tinta institucional (`civic`) para la estructura (rail, banda del cartel, acción principal, foco) y la escala de severidad solo donde la severidad significa algo. Un hallazgo cerrado no desaparece: queda sellado y tachado, como un formulario anulado, y se puede reabrir.

El movimiento es contenido y con propósito: el puntaje cuenta hasta su nuevo valor, el sello vuelve a estamparse cuando cambia la nota, las filas se expanden como acordeón y los avisos suben desde el pie. Todo respeta `prefers-reduced-motion`.

**Key Characteristics:**
- Papel frío (`paper`) de fondo, hojas casi blancas (`sheet`) con filete de 1px (`rule`) y sombra mínima.
- Tinta institucional azul (`civic`) para rail, banda del cartel, acción primaria y anillo de foco.
- Rótulos de campo en versalitas chicas (`field-label`) que siempre rotulan un dato.
- Cifras en Barlow Condensed con números tabulares; UI en Public Sans; código y rutas en JetBrains Mono.
- Severidad siempre con texto y marcas de nivel, nunca solo con color.
- Doble filete y sello como gestos propios del mundo, reservados para la nota y los estados cerrados.

## Colors

Una paleta de oficina pública: papel y tinta en la misma familia de azules fríos (tono 250–262), un azul institucional saturado como única voz estructural, y una escala de severidad cálida que solo aparece cuando hay riesgo que comunicar. Los valores canónicos están en OKLCH en `frontend/src/index.css` (`@theme`); se usan como utilidades de Tailwind (`bg-civic`, `text-ink-2`, `ring-rule`, etc.).

### Primary
- **Tinta Institucional** (`civic`): rail de navegación, banda superior del cartel de la nota, botón primario, pestaña activa, barra de progreso, enlaces y anillo de foco. Es el color de la "oficina".
- **Tinta Institucional Profunda** (`civic-deep`): hover del botón primario. No se usa en reposo.
- **Tinta sobre Institucional** (`civic-ink`): texto e íconos sobre `civic`.
- **Institucional Atenuado** (`civic-muted`): texto secundario sobre `civic` (rótulos de grupo del rail, id del escaneo en la banda, contadores de la pestaña activa).
- **Institucional Lavado** (`civic-soft`): hover de filas y botones secundarios, fila expandida, fondo de la evaluación de la IA, pista de las barras de progreso.

### Secondary
- **Tinta de Sello** (`stamp`): el sello circular del cartel y el sello "Falso positivo". Un violeta azulado que se lee como tinta de sello de goma, distinto de `civic`.
- **Verde Aprobado** (`ok`, `ok-soft`): notas A y B, y el sello "Resuelto". No es un color de severidad.

### Tertiary
Escala de severidad. Cada nivel tiene tres tonos: el color pleno (barras, celdas de crítico), `-ink` (texto legible sobre fondo claro) y `-soft` (fondo de badge).
- **Rojo Crítico** (`sev-critical`, `sev-critical-soft`): crítico, nota F, errores y toasts de error. El único badge de fondo pleno.
- **Naranja Alto** (`sev-high`, `sev-high-ink`, `sev-high-soft`): alto y nota D.
- **Ámbar Medio** (`sev-medium`, `sev-medium-ink`, `sev-medium-soft`): medio, nota C y el resaltado de la línea del hallazgo en `CodeSnippet`.
- **Azul Bajo** (`sev-low`, `sev-low-ink`, `sev-low-soft`): bajo.
- **Gris Informativo** (`sev-info`, `sev-info-ink`, `sev-info-soft`): info (inventario, no penaliza).

### Neutral
- **Papel de Formulario** (`paper`): fondo de la app, pista de barras dentro de hojas, cabecera de columnas de la tabla.
- **Hoja** (`sheet`): superficie de toda tarjeta, tabla e input. También el ítem activo del rail.
- **Tinta** (`ink`): texto principal, chip de filtro activo, fondo del toast.
- **Tinta 2** (`ink-2`): texto secundario y descripciones.
- **Tinta 3** (`ink-3`): rótulos, metadatos, rutas, íconos en reposo, texto de hallazgos cerrados.
- **Filete** (`rule`): bordes de hojas y divisores de filas; también el color del `Skeleton`.
- **Filete Marcado** (`rule-2`): borde de inputs y chips, doble filete del total, scrollbar.

### Named Rules
**La Regla de la Severidad con Sentido.** Los colores `sev-*` solo aparecen donde comunican severidad (o la nota que de ella depende). Nunca como decoración, acento de marca ni color de categoría de motor.

**La Regla de la Oficina Única.** `civic` es la única voz estructural. Una vista de módulo no introduce otro color de acento; si necesita jerarquía, usa peso, tamaño o `ink`/`ink-2`/`ink-3`.

## Typography

**Display Font:** Barlow Condensed 500/600/700 (con Public Sans Variable de respaldo)
**Body Font:** Public Sans Variable (con ui-sans-serif, system-ui)
**Label/Mono Font:** JetBrains Mono Variable, solo para código, rutas, ids, rule ids, ramas y commits

**Character:** Public Sans es la letra de un formulario gubernamental: clara, neutra, institucional. Barlow Condensed pone la voz de cartel en la letra de la nota y en las cifras grandes; nunca se usa para párrafos.

### Hierarchy
- **Display** (Barlow Condensed 700, 9rem, 1): la letra de la nota dentro del recuadro de doble filete (11rem). El cartel completo lleva también un marco de doble filete `civic`, y sus campos van en celdas con filete como la fila de la escala A–F. Una sola por pantalla, solo en el cartel.
- **Headline** (Barlow Condensed 600, 3rem, 1, tabular): el Risk Score del cartel.
- **Figure** (Barlow Condensed 600, 1.25–1.5rem, 1, tabular): cifras destacadas dentro de hojas: porcentaje del escaneo, total de penalización, conteo de abiertos por vista.
- **Page title** (Public Sans 600, 1.5rem móvil / 1.75rem desde `sm`, -0.01em): el `h1` de `PageHeader`.
- **Title** (Public Sans 600, 1rem; 1.125rem en el título de `FindingsTable`): títulos de hoja y de hallazgo.
- **Body** (Public Sans 400, 0.9375rem, 1.5): texto base del `body`. Las descripciones largas van a `text-sm` con `max-w-[75ch]`.
- **Body sm** (Public Sans 400, 0.875rem): filas, metadatos, botones, inputs.
- **Label** (Public Sans 600, 0.6875rem, 0.06em, mayúsculas, `ink-3`): la utilidad `field-label`. Rotula un dato o una columna.
- **Mono** (JetBrains Mono, 0.8125rem; 0.75rem para rule ids): rutas `archivo:línea`, código, ids.

### Named Rules
**La Regla del Rótulo con Dato.** `field-label` siempre rotula un valor que está justo debajo o en su columna (un `<dt>`, un `<th>`). Nunca flota sobre un título como antetítulo decorativo.

**La Regla de la Cifra Tabular.** Todo número que se compara o cambia (conteos, puntajes, porcentajes, fechas) lleva la utilidad `tabular`.

## Layout

Shell de dos columnas desde `lg`: rail fijo de 15.5rem a la izquierda (`sticky`, alto de viewport) y contenido a la derecha. Debajo de `lg`, el rail se convierte en una barra superior `civic` de 56px con botón de menú que abre un cajón de 17rem (máx. 85vw) con fondo `ink/40`, que se cierra con Escape, al tocar el fondo o al navegar.

Cada vista empieza con `PageHeader` y debajo un contenedor con márgenes laterales de 16px en móvil y 32px desde `sm` (`px-4 sm:px-8`), `pb-12`, y pila vertical de 20px (`space-y-5`). Las grillas de hojas usan 12 columnas desde `xl` con separación de 20px (`gap-5`) y colapsan a una columna (`grid-cols-[minmax(0,1fr)]`) por debajo. En el dashboard: cartel 5 + penalización 7, matriz 7 + accesos 5, y la tabla de hallazgos a todo el ancho.

Dentro de una hoja: encabezado de 20px horizontal por 14px vertical con filete inferior; filas de 14px vertical; padding de contenido 20px (16px en móvil). Los textos de lectura se limitan a 75ch (46ch en estados vacíos).

## Elevation & Depth

Sistema casi plano. La profundidad la dan el contraste papel/hoja y el filete de 1px (`ring-1 ring-rule`); la sombra es un apoyo ambiental mínimo, no estructura. Solo hay dos sombras, y la flotante se reserva para lo que está realmente por encima de la página.

### Shadow Vocabulary
- **Hoja** (`--shadow-sheet`, utilidad `shadow-sheet`): toda hoja apoyada sobre el papel (tablas, cartel, progreso) y el botón primario de la cabecera.
- **Flotante** (`--shadow-float`, utilidad `shadow-float`): solo cajón móvil y toast.

### Named Rules
**La Regla del Papel Apoyado.** Una hoja es `bg-sheet` + `ring-1 ring-rule` + `shadow-sheet`. No se suman sombras más fuertes, gradientes ni bordes de color a una hoja común.

## Shapes

Esquinas casi rectas, de papelería: 4px (`rounded-sm`) para hojas, botones, inputs, pestañas e ítems del rail; 2px (`rounded-xs`) para badges, sellos, celdas de la matriz, skeletons y el recuadro de la nota. Píldora (`rounded-full`) solo para barras de progreso y de proporción y para los puntos de etapa del escaneo. `--radius-md` (6px) está definido pero no se usa.

Los bordes son filetes finos (`ring-1`, `ring-inset` en controles). El **doble filete** (`border-double`) es el gesto propio del mundo: 5px en el marco del cartel y en el recuadro de la nota, 3px en los sellos de estado y en la línea de total de la penalización. Los sellos van girados (-2° el de estado, -12° el del cartel).

## Components

Todos los componentes compartidos viven en `frontend/src/components/` y se importan con el alias `@/components/...`. Antes de crear un componente nuevo en tu módulo, usá estos.

### Buttons
Firmes, de oficina: rectángulos de 4px, texto `text-sm font-semibold`, ícono lucide de 16px a la izquierda.
- **Primario** (`bg-civic text-civic-ink`, alto 40px, padding 0 16px): una sola acción principal por vista ("Nuevo escaneo", "Reintentar", "Conectar repositorio"). Hover `bg-civic-deep`; `active:scale-[0.96]`; deshabilitado con `opacity-60` y `cursor-not-allowed`.
- **Secundario** (`bg-sheet text-ink ring-1 ring-rule-2 ring-inset`, alto 36px, padding 0 12px): hover `bg-civic-soft`.
- **Enlace de acción** (`text-sm font-semibold text-civic underline decoration-civic/30`, hover `decoration-civic`): acciones dentro de estados vacíos ("Limpiar filtros", "Volver al dashboard").
- **Foco:** global, `outline 2px civic` con offset 2px. No lo sobrescribas.

### Chips
- **Filtro de severidad:** 32px de alto, `ring-1 ring-rule-2`, texto `ink-2`; activo `bg-ink text-white` con `aria-pressed`.
- **Pestañas de estado:** 36px, activas `bg-civic text-civic-ink` con contador en `civic-muted`; inactivas `ink-2` con hover `civic-soft`. Usan `role="tab"` y `aria-selected`.

### Cards / Containers
- **Corner Style:** 4px (`rounded-sm`).
- **Background:** `sheet` sobre `paper`.
- **Shadow Strategy:** `shadow-sheet` (ver Elevation & Depth).
- **Border:** `ring-1 ring-rule`; divisores internos `border-rule` / `divide-rule`.
- **Internal Padding:** encabezado `px-5 py-3.5` con `border-b`, título `text-base font-semibold`.

### Inputs / Fields
- **Style:** 36px, `bg-sheet`, `rounded-sm`, `ring-1 ring-rule-2 ring-inset`, ícono `ink-3` absoluto a 12px; placeholder `ink-3`.
- **Focus:** el anillo de foco global `civic`. Hover `ring-ink-3`.
- **Select:** `appearance-none` con `ChevronDown` superpuesto a la derecha.

### Navigation
Rail `bg-civic` con logo y "Qubitor" en Barlow Condensed (1.625rem). Grupos con rótulo en mayúsculas `civic-muted` 0.6875rem. Ítems de 40px con ícono lucide de 18px (`strokeWidth 1.75`); activo `bg-sheet text-civic font-semibold`, inactivo `civic-ink/85` con hover `white/8`. Para sumar tu vista, agregá la ruta en `frontend/src/components/layout/navigation.ts` y reemplazá su `ModulePlaceholder` en `App.tsx`.

### SeverityBadge
`<SeverityBadge severity="critical" size="md" />` (`size`: `'sm'` 20px | `'md'` 24px). Etiqueta en mayúsculas con cuatro marcas de nivel a la izquierda, para que la severidad se lea sin color. Crítico es fondo pleno; el resto, fondo `-soft` con texto `-ink`. Es la única forma de mostrar una severidad: no armes badges propios. Si necesitás las clases (barras, celdas), usá `SEVERITY_STYLES` de `@/lib/severityStyles`.

### StatusStamp
`<StatusStamp status={finding.status} />`. "Abierto" es texto plano en mayúsculas `ink-2`; "Resuelto" (`ok`) y "Falso positivo" (`stamp`) son sellos de doble filete de 3px girados -2°. Acompañalo siempre con la fila atenuada: título `line-through` en `ink-3` y badge al 55 % de opacidad.

### FindingStatusActions
`<FindingStatusActions finding={f} onChange={(status) => ...} pending={bool} />`. Si el hallazgo está abierto muestra "Marcar resuelto" (primario) y "Falso positivo" (secundario); si está cerrado, "Reabrir". `pending` deshabilita mientras se guarda. El cambio se aplica de forma optimista y se confirma con un toast con "Deshacer" (ver `useToast`).

### FindingCard
`<FindingCard finding={f} actions={<FindingStatusActions ... />} hideHeader={false} />`. Ficha de un hallazgo: encabezado con badge, título, rule id y sello; campos rotulados (Archivo, Motor, CWE, CVE, severidad original si la IA la ajustó); descripción; `CodeSnippet`; y la evaluación de la IA en un recuadro `civic-soft/60` con ícono `Sparkles`. Usá `hideHeader` cuando la fila que la contiene ya muestra título y severidad.

### FindingsTable
`<FindingsTable findings={...} onStatusChange={(f, status) => ...} pendingIds={set} engines={['sast']} initialStatus="open" title="Hallazgos" />`. Tabla completa con pestañas de estado, filtros de severidad, motor y texto, orden fijo por severidad efectiva y ubicación (la fila no salta al cambiar de estado), y filas que se expanden en acordeón con la `FindingCard`. En una vista de módulo, pasá `engines` con tu motor para acotar el filtro. Sin `onStatusChange` la tabla es de solo lectura.

### CodeSnippet
`<CodeSnippet code={snippet} line={42} startLine={40} filePath="app/db.py" />`. Única superficie oscura del sistema: azul tinta casi negro, números de línea tabulares y la línea del hallazgo resaltada en ámbar (`sev-medium`). Los snippets llegan con secretos enmascarados; nunca muestres un secreto en claro.

### EmptyState
`<EmptyState icon={SearchX} title="..." description="..." action={...} tone="neutral" />` (`tone`: `'neutral' | 'error'`). Centrado, ícono en un cuadro de 44px (`civic-soft` o `sev-critical-soft` en error), título, descripción de hasta 46ch y una acción que destraba la pantalla. Todo vacío y todo error usan esto; dentro de una hoja, envolvelo en el contenedor de hoja.

### Loader / Skeleton
`<Loader label="Cargando hallazgos…" />` para esperas en línea (anunciado con `role="status"`). `<Skeleton className="h-8 w-72" />` para bloques: imitá la forma real de la vista (cabecera, grilla de hojas, tabla) como hace `DashboardSkeleton`. El contenido que llega entra con `t-reveal`.

### ScanProgress
`<ScanProgress scan={liveScan} error={pollError} />`, alimentado por `useScanPolling` de `@/hooks/useScanPolling`. Hoja con titular de estado, porcentaje en Barlow Condensed, barra `civic` (indeterminada mientras está en cola, roja si falla) y las seis etapas del pipeline con su estado.

### PageHeader
`<PageHeader title="Secretos" meta={<span>…</span>} actions={<button …>} />`. Encabezado de toda vista: `h1` a la izquierda, línea de contexto (repo, rama, commit, fecha, separados por `·`) y acciones a la derecha. Lleva su propio padding; el contenido siguiente va en `px-4 pb-12 sm:px-8`.

### useToast
`const toast = useToast(); toast({ message, action: { label: 'Deshacer', onClick }, tone: 'error' })`. Un aviso a la vez al pie (centrado en móvil, a la derecha desde `sm`), fondo `ink` (o `sev-critical` en error), 5 s visible, pausa al pasar el mouse. Usalo para confirmar cambios de estado y errores de red; no para información que debería estar en la página.

### GradeNotice (firma)
El cartel de la nota del dashboard: banda `civic` con el título en Barlow Condensed en mayúsculas, la letra en un recuadro de doble filete de 5px con el sello en su esquina, los campos en celdas con filete, el Risk Score que cuenta hasta su valor, una regla 0–100 con los cortes, la escala A–F con la nota actual rellena, y el sello circular `stamp` que se vuelve a estampar cuando cambia la nota. Es exclusivo del dashboard general; los módulos no lo replican.

### Motion
Recetas en `index.css`: acordeón (`t-acc`, 250ms), toast (`t-toast`, 350ms entrada / 250ms salida), skeleton (`t-skeleton`, 1.4s), revelado (`t-reveal`, 400ms) e indeterminado (`t-indeterminate`). Curva por defecto `--ease-swift`. Las barras animan su ancho en 700ms. Al apuntar una fila de la matriz o de los accesos, el resto baja a 45 % de opacidad. Todo se apaga con `prefers-reduced-motion`.

### Dónde trabaja cada módulo
Cada módulo construye sus vistas solo en `frontend/src/features/<módulo>/` (`code`, `secrets`, `pqc`, `dependencies`, `history`, `connect`). Lo compartido (componentes, `lib/`, `hooks/`, `types/`, `index.css`) no se modifica desde un módulo: si falta algo, se propone en un PR revisado por el Módulo B. Para publicar tu vista, reemplazá su `ModulePlaceholder` en `App.tsx` por tu página.

## Do's and Don'ts

### Do:
- **Do** apoyar todo contenido en hojas `bg-sheet ring-1 ring-rule shadow-sheet rounded-sm` sobre el fondo `paper`.
- **Do** mostrar severidad solo con `SeverityBadge` o `SEVERITY_STYLES`, siempre con su texto.
- **Do** rotular datos con `field-label` y poner `tabular` en toda cifra que cambia o se compara.
- **Do** usar JetBrains Mono para rutas, código, rule ids, ramas y commits, y nada más.
- **Do** dejar los hallazgos cerrados en su lugar, tachados y con `StatusStamp`, con opción de reabrir y toast con "Deshacer".
- **Do** cubrir los cuatro estados de cada vista: carga (`Skeleton`), error (`EmptyState tone="error"` con "Reintentar"), vacío (`EmptyState` con la acción que destraba) y datos.
- **Do** usar íconos lucide con `strokeWidth` 1.75 (2 en botones) y `aria-hidden`.

### Don't:
- **Don't** armar filas de KPIs con número grande + etiqueta + acento de color; las cifras viven dentro de su hoja con su rótulo.
- **Don't** usar colores `sev-*` como decoración, color de marca o de motor.
- **Don't** introducir otro color de acento además de `civic`, ni fondos con gradiente.
- **Don't** poner antetítulos o rótulos en mayúsculas sobre un título; `field-label` solo rotula datos.
- **Don't** usar Barlow Condensed para párrafos o texto de UI corriente, ni una fuente del sistema para cifras grandes.
- **Don't** usar sombras más fuertes que `shadow-sheet` en contenido de página; `shadow-float` es solo para cajón y toast.
- **Don't** replicar el cartel de la nota ni su sello fuera del dashboard general.
- **Don't** mostrar un secreto en claro: los snippets se muestran tal como llegan, enmascarados.
