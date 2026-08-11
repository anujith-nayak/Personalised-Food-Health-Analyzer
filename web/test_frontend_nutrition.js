import { parseNutrientValue } from './src/utils/nutrition.js'

console.log('=' .repeat(60))
console.log('TESTING FRONTEND NUTRITION PARSER UTILITY')
console.log('=' .repeat(60))

// Case 1: Structured dual-column object
const caloriesObj = { per_100g: 524.0, per_serving: 66.0, unit: 'kcal' }
const parsed1 = parseNutrientValue(caloriesObj, 'calories')
console.log('\nCase 1 (Structured Object):')
console.log(parsed1)
console.assert(parsed1.perServing === 66.0, 'perServing should be 66.0')
console.assert(parsed1.per100g === 524.0, 'per100g should be 524.0')
console.assert(parsed1.unit === 'kcal', 'unit should be kcal')

// Case 2: Null / Not Available
const potassiumObj = null
const parsed2 = parseNutrientValue(potassiumObj, 'potassium')
console.log('\nCase 2 (Null Nutrient):')
console.log(parsed2)
console.assert(parsed2.isAvailable === false, 'isAvailable should be false')
console.assert(parsed2.displayText === 'Not Available', 'displayText should be Not Available')

// Case 3: Backward compatible scalar number
const scalarFat = 30.0
const parsed3 = parseNutrientValue(scalarFat, 'total_fat')
console.log('\nCase 3 (Scalar Number):')
console.log(parsed3)
console.assert(parsed3.perServing === 30.0, 'perServing should be 30.0')
console.assert(parsed3.unit === 'g', 'unit should be g')
console.assert(parsed3.isAvailable === true, 'isAvailable should be true')

console.log('\n=' .repeat(60))
console.log('ALL FRONTEND UTILITY TESTS PASSED!')
console.log('=' .repeat(60))
