/// Model for the packaged food analysis API response
class FoodScanResult {
  final String productName;
  final List<String> ingredients;
  final Map<String, dynamic> nutritionFacts;
  final int healthScore;        // 0-100, HIGHER = safer
  final String riskLevel;
  final String riskColor;
  final String riskAdvice;
  final List<String> reasons;
  final List<String> affectedConditions;
  final List<dynamic> thresholdSummary;
  final List<dynamic> allergyAlerts;
  final bool hasCriticalAllergen;
  final List<String> foodsToAvoid;
  final List<String> betterAlternatives;
  final List<String> recommendedFoods;
  final List<String> servingAdvice;
  final List<String> userConditions;
  final String personalizedFor;
  final String? userBp;
  final double? userSugar;
  final double? userBmi;

  const FoodScanResult({
    required this.productName,
    required this.ingredients,
    required this.nutritionFacts,
    required this.healthScore,
    required this.riskLevel,
    required this.riskColor,
    required this.riskAdvice,
    required this.reasons,
    required this.affectedConditions,
    required this.thresholdSummary,
    required this.allergyAlerts,
    required this.hasCriticalAllergen,
    required this.foodsToAvoid,
    required this.betterAlternatives,
    required this.recommendedFoods,
    required this.servingAdvice,
    required this.userConditions,
    required this.personalizedFor,
    this.userBp,
    this.userSugar,
    this.userBmi,
  });

  factory FoodScanResult.fromJson(Map<String, dynamic> j) => FoodScanResult(
        productName:         j['product_name'] ?? 'Unknown',
        ingredients:         List<String>.from(j['ingredients'] ?? []),
        nutritionFacts:      Map<String, dynamic>.from(j['nutrition_facts'] ?? {}),
        healthScore:         j['health_score'] ?? (100 - (j['risk_score'] ?? 0)),
        riskLevel:           j['risk_level'] ?? 'Unknown',
        riskColor:           j['risk_color'] ?? 'gray',
        riskAdvice:          j['risk_advice'] ?? '',
        reasons:             List<String>.from(j['reasons'] ?? []),
        affectedConditions:  List<String>.from(j['affected_conditions'] ?? []),
        thresholdSummary:    List<dynamic>.from(j['threshold_summary'] ?? []),
        allergyAlerts:       List<dynamic>.from(j['allergy_alerts'] ?? []),
        hasCriticalAllergen: j['has_critical_allergen'] ?? false,
        foodsToAvoid:        List<String>.from(j['foods_to_avoid'] ?? []),
        betterAlternatives:  List<String>.from(j['better_alternatives'] ?? []),
        recommendedFoods:    List<String>.from(j['recommended_foods'] ?? []),
        servingAdvice:       List<String>.from(j['serving_advice'] ?? []),
        userConditions:      List<String>.from(j['user_conditions'] ?? []),
        personalizedFor:     j['personalized_for'] ?? '',
        userBp:              j['user_bp'],
        userSugar:           j['user_sugar'] != null ? (j['user_sugar'] as num).toDouble() : null,
        userBmi:             j['user_bmi']   != null ? (j['user_bmi']   as num).toDouble() : null,
      );
}
