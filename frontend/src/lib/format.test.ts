import { describe, expect, it } from 'vitest'
import { pluralize } from './format'

describe('pluralize', () => {
  it('usa el singular solo para 1', () => {
    expect(pluralize(1, 'repositorio', 'repositorios')).toContain('repositorio')
    expect(pluralize(2, 'repositorio', 'repositorios')).toContain('repositorios')
  })
})
