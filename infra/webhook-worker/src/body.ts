/** Lectura del cuerpo con tope de tamaño, sin cargar en memoria más de lo permitido. */

export class BodyTooLarge extends Error {}

export async function readBodyLimited(request: Request, maxBytes: number): Promise<ArrayBuffer> {
  const declared = Number(request.headers.get('Content-Length') ?? '0')
  if (declared > maxBytes) throw new BodyTooLarge()
  if (!request.body) return new ArrayBuffer(0)

  const reader = request.body.getReader()
  const chunks: Uint8Array[] = []
  let total = 0
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    total += value.byteLength
    if (total > maxBytes) {
      await reader.cancel()
      throw new BodyTooLarge()
    }
    chunks.push(value)
  }
  const body = new Uint8Array(total)
  let offset = 0
  for (const chunk of chunks) {
    body.set(chunk, offset)
    offset += chunk.byteLength
  }
  return body.buffer
}
