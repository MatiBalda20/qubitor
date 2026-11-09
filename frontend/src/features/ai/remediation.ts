/**
 * Pasos de remediación a partir del texto de la IA.
 *
 * Gemini devuelve la remediación como texto libre: a veces en líneas numeradas,
 * a veces con guiones y a veces en un solo párrafo. Se separa en pasos para
 * mostrarlos como lista; si no hay forma de separarlos, queda un solo paso.
 */
export function remediationSteps(text: string | null | undefined): string[] {
  if (!text) return []
  const lines = text
    .split(/\r?\n/)
    .map((line) => line.replace(/^\s*(?:\d+[.)]|[-*•])\s*/, '').trim())
    .filter(Boolean)
  return lines
}
