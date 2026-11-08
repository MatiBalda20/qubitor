import { defineConfig, mergeConfig } from 'vitest/config'
import viteConfig from './vite.config'

/** Tests de componentes y lógica del frontend (Vitest + Testing Library en jsdom). */
export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: 'jsdom',
      setupFiles: ['./src/test/setup.ts'],
      // Los tests usan siempre los mock.json: nunca llaman a una API real.
      env: { VITE_API_URL: '', VITE_USE_MOCKS: 'true', VITE_CLERK_PUBLISHABLE_KEY: '' },
      restoreMocks: true,
    },
  }),
)
