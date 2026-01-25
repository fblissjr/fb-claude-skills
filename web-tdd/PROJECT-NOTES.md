# Project-Specific Notes

This skill adapts to different project types. Here's how it applies to your two main projects:

## Tabidachi (Japan Travel App)

**Stack:** React + TypeScript + Tailwind, Zustand, Leaflet/Google Maps, Gemini API

**Test Focus:**
- Component tests for UI (PlaceDetail, ItineraryView, TripSetup)
- Hook tests (useMapNavigation, custom Zustand selectors)
- AI service mocking (mock Gemini responses)
- E2E for critical user journeys (search → save → plan)
- Mobile responsive tests (sidebar collapse, touch interactions)

**Recommended Setup:**
```bash
# Already has Vitest? Check:
grep vitest package.json

# If not:
npm install -D vitest @vitest/ui jsdom
npm install -D @testing-library/react @testing-library/jest-dom

# E2E (Playwright recommended for visual regression)
npm install -D @playwright/test
npx playwright install
```

**Key Tests to Write:**
1. `PlaceDetail.test.tsx` - Priority toggle, "more/less like this" 
2. `ai.test.ts` - Mock Gemini, test route calculation logic
3. `e2e/trip-planning.spec.ts` - Full flow: search → add place → build itinerary

**Mocking Strategy:**
```typescript
// Mock Gemini AI calls
vi.mock('../services/ai', () => ({
  discoverPlaces: vi.fn().mockResolvedValue([
    { id: '1', name: 'Test Place', lat: 35.6762, lng: 139.6503 }
  ]),
  generateRouteOptions: vi.fn().mockResolvedValue([
    { id: 'route1', totalTime: 180, transfers: 2 }
  ])
}))
```

---

## llm-dit-experiments (ML Pipeline UI)

**Stack:** React (vNext) + Python (FastAPI), schema-driven forms, ML pipelines

**Test Focus:**
- Schema → Form rendering (ParamSchema generates correct controls)
- Parameter validation (min/max/step enforcement)
- Conditional visibility (show X when Y enabled)
- Progressive disclosure (basic → advanced → expert)
- Visual regression (UI consistency across schema changes)
- Backend: Pipeline execution, model pool, orchestration

**Recommended Setup:**

Frontend:
```bash
cd frontend
npm install -D vitest @vitest/ui jsdom
npm install -D @testing-library/react @testing-library/jest-dom

# Playwright for visual regression
npm install -D @playwright/test
```

Backend:
```bash
cd backend  # or wherever Python lives
uv add pytest pytest-asyncio httpx --dev
```

**Key Tests to Write:**

1. **Schema rendering** - Core value prop
```typescript
// components/DynamicForm.test.tsx
it('renders slider for range param', () => {
  const schema: ParamSchema = {
    id: 'steps',
    type: 'range',
    min: 1,
    max: 100,
    default: 20
  }
  render(<DynamicForm schema={[schema]} />)
  
  expect(screen.getByRole('slider')).toHaveAttribute('min', '1')
  expect(screen.getByRole('slider')).toHaveAttribute('max', '100')
})

it('shows conditional params when toggle enabled', async () => {
  const schema: ParamSchema[] = [
    { id: 'creative_mode', type: 'checkbox', default: false },
    { id: 'temperature', type: 'range', conditional: { creative_mode: true } }
  ]
  render(<DynamicForm schema={schema} />)
  
  expect(screen.queryByLabelText('temperature')).not.toBeInTheDocument()
  
  await userEvent.click(screen.getByLabelText('creative_mode'))
  
  expect(screen.getByLabelText('temperature')).toBeInTheDocument()
})
```

2. **Visual regression** - Catch UI breakage
```typescript
// e2e/visual.spec.ts
test('zimage form matches snapshot', async ({ page }) => {
  await page.goto('/pipeline/zimage')
  await expect(page).toHaveScreenshot('zimage-form.png')
})

test('progressive disclosure works', async ({ page }) => {
  await page.goto('/pipeline/zimage')
  await page.click('[data-testid=show-advanced]')
  await expect(page).toHaveScreenshot('zimage-advanced.png')
})
```

3. **Backend pipeline tests**
```python
# tests/test_schemas.py
def test_param_schema_validation():
    schema = ParamSchema(id="steps", type="range", min=1, max=100)
    
    assert schema.validate(50) == True
    assert schema.validate(101) == False  # exceeds max

# tests/test_generation.py
@pytest.mark.asyncio
async def test_zimage_generation():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/generate/zimage", json={
            "prompt": "a cat",
            "steps": 20,
            "width": 512,
            "height": 512
        })
    
    assert response.status_code == 200
    assert "image_url" in response.json()
```

**Agent-Friendly Testing:**
Since Claude/agents will modify schemas, ensure tests validate:
1. Schema changes don't break form rendering
2. New params appear in correct groups
3. Conditional logic works as expected

```typescript
// This test ensures agents can safely add params
it('handles unknown param types gracefully', () => {
  const schema: ParamSchema = {
    id: 'future_param',
    type: 'unknown_type' as any,
    default: 'test'
  }
  
  // Should render fallback (text input) not crash
  render(<DynamicForm schema={[schema]} />)
  expect(screen.getByRole('textbox')).toBeInTheDocument()
})
```
