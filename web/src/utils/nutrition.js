/**
 * Utility functions for normalizing and displaying nutrition data across frontend components.
 * Supports both new structured nutrient objects ({ per_100g, per_serving, unit })
 * and backward-compatible scalar values (e.g. 524 or "524").
 */

export function getFallbackUnit(key = '') {
  if (!key) return 'g'
  const k = key.toLowerCase()
  if (k.includes('calorie') || k === 'energy') return 'kcal'
  if (
    k.includes('sodium') ||
    k.includes('cholesterol') ||
    k.includes('potassium') ||
    k.includes('calcium') ||
    k.includes('iron')
  ) {
    return 'mg'
  }
  return 'g'
}

export function parseNutrientValue(val, key = '') {
  const fallbackUnit = getFallbackUnit(key)

  if (val === null || val === undefined) {
    return {
      per100g: null,
      perServing: null,
      unit: fallbackUnit,
      raw: null,
      isAvailable: false,
      displayText: 'Not Available',
    }
  }

  if (typeof val === 'object' && !Array.isArray(val)) {
    const per100g = val.per_100g !== undefined && val.per_100g !== null ? val.per_100g : null
    const perServing = val.per_serving !== undefined && val.per_serving !== null ? val.per_serving : null
    const unit = val.unit || fallbackUnit
    const isAvailable = per100g !== null || perServing !== null

    return {
      per100g,
      perServing,
      unit,
      raw: val,
      isAvailable,
      displayText: isAvailable
        ? (perServing !== null ? `${perServing} ${unit}` : `${per100g} ${unit}`)
        : 'Not Available',
    }
  }

  // Handle scalar (old API responses or primitive numbers)
  const num = typeof val === 'number' ? val : parseFloat(val)
  const isValidNum = !isNaN(num)
  const unit = fallbackUnit

  return {
    per100g: null,
    perServing: isValidNum ? num : null,
    unit,
    raw: val,
    isAvailable: isValidNum,
    displayText: isValidNum ? `${num} ${unit}` : 'Not Available',
  }
}
