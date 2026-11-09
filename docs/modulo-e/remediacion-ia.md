# Módulo E — Panel de remediación y resumen ejecutivo (frontend)

## Panel de remediación (`features/ai/AiTriagePanel.tsx`)

Muestra la evaluación de la IA de un hallazgo:

- si parece un **falso positivo** (y que entonces no cuenta para el Risk Score);
- el **cambio de severidad** motor → IA;
- la **explicación** para el líder técnico;
- la **remediación**, separada en pasos cuando la IA la devuelve numerada o con guiones;
- un aviso de que es contenido generado por IA.

Sin triage no muestra nada.

**Reutilizable:** `FindingCard` (componente compartido) usa el panel en lugar de su bloque de triage anterior. Por eso aparece en el dashboard general y en cualquier vista que use `FindingCard` o `FindingsTable`, como las vistas «Secretos», «Código inseguro», «Post-cuántica» y «Dependencias» de los Módulos C y D, sin que esos módulos cambien nada. También se puede usar suelto:

```tsx
import { AiTriagePanel } from '@/features/ai/AiTriagePanel'

<AiTriagePanel finding={finding} />                            // con el cambio de severidad
<AiTriagePanel finding={finding} showSeverityChange={false} />  // si la vista ya muestra la severidad del motor
```

El texto de la IA se renderiza siempre escapado por React, nunca como HTML. Además, el backend lo enmascara antes de guardarlo.

## Tarjeta de resumen ejecutivo (`features/ai/ExecutiveSummaryCard.tsx`)

Va arriba del dashboard general (`DashboardPage`, Módulo B) y consulta `GET /scans/{id}/summary` del último escaneo terminado. Muestra:

- el titular y un párrafo en lenguaje de negocio;
- los tres riesgos principales, con impacto y prioridad;
- «Qué hacer primero».

Indica si el resumen se **generó con IA** o es el **automático sin IA** (fallback heurístico del backend), y avisa cuando la IA no evaluó todos los hallazgos por cuota agotada, Gemini caído o sin configurar. Si la carga falla, lo dice dentro de la tarjeta y el resto del dashboard sigue funcionando.

## Cambios fuera de `features/ai/`

Para revisión del Módulo B:

- `components/FindingCard.tsx`: reemplaza el bloque de triage inline por `<AiTriagePanel showSeverityChange={false} />`. La «Severidad del motor» sigue en los datos de la tarjeta.
- `features/dashboard/DashboardPage.tsx`: agrega `<ExecutiveSummaryCard scanId={scan.id} />` antes de la nota y las matrices.
- `src/test/setup.ts`: `matchMedia` mínimo para jsdom.

## Probar

```bash
cd frontend
npm test     # panel, pasos de remediación, tarjeta (IA, heurístico, cuota, sin resumen, error) y dashboard integrado
VITE_USE_MOCKS=true npm run dev   # http://localhost:5173/ con el resumen de ejemplo
```
