/**
 * Punto de entrada del Worker de webhooks de GitHub (Módulo E). La lógica está en handler.ts.
 *
 * Este módulo solo exporta el handler por defecto: el runtime de Workers trata
 * cada export con nombre del módulo principal como otro punto de entrada y
 * rechaza el Worker si alguno no es una función o un handler (por ejemplo, una
 * constante). Por eso las constantes y `handleRequest` viven en handler.ts.
 */

import { handleRequest } from './handler'

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    return handleRequest(request, env)
  },
} satisfies ExportedHandler<Env>
