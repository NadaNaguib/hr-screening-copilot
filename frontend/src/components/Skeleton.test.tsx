import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Skeleton } from './Skeleton'

describe('Skeleton', () => {
  it('renders with default classes', () => {
    render(<Skeleton className="h-10 w-full" data-testid="skeleton" />)
    const el = screen.getByTestId('skeleton')
    expect(el).toBeInTheDocument()
    expect(el.className).toContain('animate-pulse')
    expect(el.className).toContain('bg-surface-border')
    expect(el.className).toContain('h-10')
    expect(el.className).toContain('w-full')
  })

  it('renders without extra className', () => {
    render(<Skeleton data-testid="bare" />)
    const el = screen.getByTestId('bare')
    expect(el).toBeInTheDocument()
    expect(el.className).toContain('rounded-md')
  })
})
