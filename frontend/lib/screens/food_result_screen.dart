import 'package:flutter/material.dart';
import '../models/food_scan_result.dart';
import '../widgets/info_card.dart';

class FoodResultScreen extends StatelessWidget {
  final FoodScanResult result;
  const FoodResultScreen({super.key, required this.result});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Analysis Result'),
        actions: [
          TextButton.icon(
            icon: const Icon(Icons.camera_alt_outlined),
            label: const Text('Scan Again'),
            onPressed: () => Navigator.pop(context),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // ── Health Score Card ─────────────────────────────────────────
          _HealthScoreCard(result: result),
          const SizedBox(height: 12),

          // ── User Health Context ───────────────────────────────────────
          if (result.userBp != null || result.userSugar != null || result.userBmi != null)
            _UserContextCard(result: result),
          if (result.userBp != null || result.userSugar != null || result.userBmi != null)
            const SizedBox(height: 12),

          // ── Critical Allergen Alert ───────────────────────────────────
          if (result.hasCriticalAllergen) ...[
            _CriticalAllergenBanner(alerts: result.allergyAlerts),
            const SizedBox(height: 12),
          ],

          // ── Product Name ──────────────────────────────────────────────
          InfoCard(
            title: 'Product',
            icon: Icons.inventory_2_outlined,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(result.productName,
                    style: Theme.of(context)
                        .textTheme
                        .titleMedium
                        ?.copyWith(fontWeight: FontWeight.bold)),
                const SizedBox(height: 4),
                Text('Personalised for: ${result.personalizedFor}',
                    style: Theme.of(context)
                        .textTheme
                        .bodySmall
                        ?.copyWith(color: Colors.grey[600])),
              ],
            ),
          ),
          const SizedBox(height: 12),

          // ── Detected Ingredients ──────────────────────────────────────
          if (result.ingredients.isNotEmpty)
            InfoCard(
              title: 'Detected Ingredients',
              icon: Icons.list_alt,
              child: Wrap(
                spacing: 6, runSpacing: 6,
                children: result.ingredients
                    .map((i) => Chip(
                          label: Text(i, style: const TextStyle(fontSize: 12)),
                          padding: EdgeInsets.zero,
                          visualDensity: VisualDensity.compact,
                        ))
                    .toList(),
              ),
            ),
          if (result.ingredients.isNotEmpty) const SizedBox(height: 12),

          // ── Nutrition Facts ───────────────────────────────────────────
          if (result.nutritionFacts.isNotEmpty)
            InfoCard(
              title: 'Nutrition Facts',
              icon: Icons.bar_chart,
              child: Column(
                children: result.nutritionFacts.entries.map((e) {
                  return Padding(
                    padding: const EdgeInsets.symmetric(vertical: 3),
                    child: Row(children: [
                      Text(_formatName(e.key),
                          style: const TextStyle(
                              fontWeight: FontWeight.w500, fontSize: 13)),
                      const Spacer(),
                      Text('${e.value} ${_unitFor(e.key)}',
                          style: TextStyle(
                              fontSize: 13, color: Colors.grey[700])),
                    ]),
                  );
                }).toList(),
              ),
            ),
          if (result.nutritionFacts.isNotEmpty) const SizedBox(height: 12),

          // ── Threshold Exceeded Table ──────────────────────────────────
          if (result.thresholdSummary.isNotEmpty)
            InfoCard(
              title: 'Threshold Analysis',
              icon: Icons.analytics_outlined,
              child: Column(
                children: result.thresholdSummary.map<Widget>((t) {
                  final item = Map<String, dynamic>.from(t);
                  final pct  = item['percent_used'] as int? ?? 0;
                  final color = pct > 150
                      ? Colors.red
                      : pct > 100
                          ? Colors.orange
                          : Colors.amber[700]!;
                  return Container(
                    margin: const EdgeInsets.only(bottom: 8),
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: color.withOpacity(0.08),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: color.withOpacity(0.3)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(children: [
                          Text('${item['nutrient']} (${item['condition']})',
                              style: TextStyle(
                                  fontWeight: FontWeight.bold,
                                  fontSize: 13,
                                  color: color)),
                          const Spacer(),
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 8, vertical: 2),
                            decoration: BoxDecoration(
                              color: color,
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: Text('$pct%',
                                style: const TextStyle(
                                    color: Colors.white,
                                    fontSize: 11,
                                    fontWeight: FontWeight.bold)),
                          ),
                        ]),
                        const SizedBox(height: 4),
                        Text(
                          'Your intake: ${item['your_value']}${item['unit']}  '
                          '|  Safe limit: ${item['safe_limit']}${item['unit']}/day  '
                          '|  ${item['restriction']}',
                          style: const TextStyle(fontSize: 12),
                        ),
                        // Progress bar
                        const SizedBox(height: 6),
                        ClipRRect(
                          borderRadius: BorderRadius.circular(4),
                          child: LinearProgressIndicator(
                            value: (pct / 100).clamp(0.0, 3.0) / 3.0,
                            backgroundColor: Colors.grey[200],
                            valueColor:
                                AlwaysStoppedAnimation<Color>(color),
                            minHeight: 6,
                          ),
                        ),
                      ],
                    ),
                  );
                }).toList(),
              ),
            ),
          if (result.thresholdSummary.isNotEmpty) const SizedBox(height: 12),

          // ── Reasons ───────────────────────────────────────────────────
          if (result.reasons.isNotEmpty)
            InfoCard(
              title: 'Detailed Analysis',
              icon: Icons.info_outline,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: result.reasons
                    .map((r) => Padding(
                          padding: const EdgeInsets.symmetric(vertical: 4),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Icon(Icons.warning_amber_outlined,
                                  size: 15,
                                  color: Theme.of(context).colorScheme.error),
                              const SizedBox(width: 6),
                              Expanded(
                                  child: Text(r,
                                      style: const TextStyle(fontSize: 12))),
                            ],
                          ),
                        ))
                    .toList(),
              ),
            ),
          if (result.reasons.isNotEmpty) const SizedBox(height: 12),

          // ── Affected Conditions ───────────────────────────────────────
          if (result.affectedConditions.isNotEmpty)
            InfoCard(
              title: 'Affected Conditions',
              icon: Icons.health_and_safety_outlined,
              child: Wrap(
                spacing: 6, runSpacing: 6,
                children: result.affectedConditions
                    .map((c) => Chip(
                          label: Text(c,
                              style: const TextStyle(
                                  fontSize: 12, color: Colors.white)),
                          backgroundColor: Colors.red[400],
                          padding: EdgeInsets.zero,
                          visualDensity: VisualDensity.compact,
                        ))
                    .toList(),
              ),
            ),
          if (result.affectedConditions.isNotEmpty) const SizedBox(height: 12),

          // ── Allergy Alerts ────────────────────────────────────────────
          if (result.allergyAlerts.isNotEmpty)
            InfoCard(
              title: 'Allergy Warnings',
              icon: Icons.no_food_outlined,
              child: Column(
                children: result.allergyAlerts.map<Widget>((a) {
                  final alert = Map<String, dynamic>.from(a);
                  final severity = alert['severity'] ?? 'Moderate';
                  final color = severity == 'Severe'
                      ? Colors.red
                      : severity == 'Moderate'
                          ? Colors.orange
                          : Colors.amber[700]!;
                  return Container(
                    margin: const EdgeInsets.only(bottom: 8),
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: color.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: color.withOpacity(0.4)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(children: [
                          Icon(Icons.warning, size: 16, color: color),
                          const SizedBox(width: 6),
                          Text(
                            '${alert['allergen']} — $severity',
                            style: TextStyle(
                                fontWeight: FontWeight.bold,
                                color: color,
                                fontSize: 13),
                          ),
                        ]),
                        const SizedBox(height: 3),
                        Text(
                          'Contains: ${alert['matched_ingredient']}  ·  ${alert['recommendation']}',
                          style: const TextStyle(fontSize: 12),
                        ),
                      ],
                    ),
                  );
                }).toList(),
              ),
            ),
          if (result.allergyAlerts.isNotEmpty) const SizedBox(height: 12),

          // ── Foods to Avoid ────────────────────────────────────────────
          if (result.foodsToAvoid.isNotEmpty)
            InfoCard(
              title: 'Foods to Avoid',
              icon: Icons.block_outlined,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: result.foodsToAvoid
                    .map((f) => Padding(
                          padding: const EdgeInsets.symmetric(vertical: 3),
                          child: Row(children: [
                            Icon(Icons.close,
                                size: 15,
                                color: Theme.of(context).colorScheme.error),
                            const SizedBox(width: 8),
                            Text(f, style: const TextStyle(fontSize: 13)),
                          ]),
                        ))
                    .toList(),
              ),
            ),
          if (result.foodsToAvoid.isNotEmpty) const SizedBox(height: 12),

          // ── Better Alternatives ───────────────────────────────────────
          if (result.betterAlternatives.isNotEmpty)
            InfoCard(
              title: 'Better Alternatives',
              icon: Icons.swap_horiz,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: result.betterAlternatives
                    .map((f) => Padding(
                          padding: const EdgeInsets.symmetric(vertical: 3),
                          child: Row(children: [
                            Icon(Icons.check, size: 15, color: Colors.green[600]),
                            const SizedBox(width: 8),
                            Expanded(
                                child: Text(f,
                                    style: const TextStyle(fontSize: 13))),
                          ]),
                        ))
                    .toList(),
              ),
            ),
          if (result.betterAlternatives.isNotEmpty) const SizedBox(height: 12),

          // ── Recommended Foods ─────────────────────────────────────────
          if (result.recommendedFoods.isNotEmpty)
            InfoCard(
              title: 'Recommended for You',
              icon: Icons.restaurant_menu,
              child: Wrap(
                spacing: 6, runSpacing: 6,
                children: result.recommendedFoods
                    .map((f) => Chip(
                          label: Text(f,
                              style: const TextStyle(
                                  fontSize: 12, color: Colors.white)),
                          backgroundColor: Colors.green[600],
                          padding: EdgeInsets.zero,
                          visualDensity: VisualDensity.compact,
                        ))
                    .toList(),
              ),
            ),
          if (result.recommendedFoods.isNotEmpty) const SizedBox(height: 12),

          // ── Serving Advice ────────────────────────────────────────────
          if (result.servingAdvice.isNotEmpty)
            InfoCard(
              title: 'Serving Advice',
              icon: Icons.tips_and_updates_outlined,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: result.servingAdvice
                    .map((a) => Padding(
                          padding: const EdgeInsets.symmetric(vertical: 3),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Icon(Icons.lightbulb_outline,
                                  size: 15, color: Colors.amber[700]),
                              const SizedBox(width: 8),
                              Expanded(
                                  child: Text(a,
                                      style: const TextStyle(fontSize: 13))),
                            ],
                          ),
                        ))
                    .toList(),
              ),
            ),
          const SizedBox(height: 32),
        ],
      ),
    );
  }

  String _formatName(String key) => key
      .replaceAll('_', ' ')
      .split(' ')
      .map((w) => w.isNotEmpty ? w[0].toUpperCase() + w.substring(1) : '')
      .join(' ');

  String _unitFor(String key) {
    if (key == 'calories') return 'kcal';
    if (key == 'sodium')   return 'mg';
    return 'g';
  }
}

// ── Health Score Hero ─────────────────────────────────────────────────────────

class _HealthScoreCard extends StatelessWidget {
  final FoodScanResult result;
  const _HealthScoreCard({required this.result});

  Color _riskColor(BuildContext context) {
    switch (result.riskColor) {
      case 'green':   return Colors.green;
      case 'yellow':  return Colors.amber[600]!;
      case 'orange':  return Colors.orange;
      case 'red':     return Colors.red;
      case 'darkred': return Colors.red[900]!;
      default:        return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) {
    final color = _riskColor(context);
    final score = result.healthScore;

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [color.withOpacity(0.15), color.withOpacity(0.04)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color.withOpacity(0.4), width: 2),
      ),
      child: Column(
        children: [
          Row(children: [
            // Score circle
            Container(
              width: 84,
              height: 84,
              decoration: BoxDecoration(shape: BoxShape.circle, color: color),
              child: Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text('$score',
                        style: const TextStyle(
                            color: Colors.white,
                            fontSize: 28,
                            fontWeight: FontWeight.black)),
                    Text('/100',
                        style: TextStyle(
                            color: Colors.white.withOpacity(0.8),
                            fontSize: 11)),
                  ],
                ),
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(result.riskLevel,
                      style: TextStyle(
                          color: color,
                          fontSize: 22,
                          fontWeight: FontWeight.black)),
                  const SizedBox(height: 4),
                  Text(result.riskAdvice,
                      style: TextStyle(
                          fontSize: 13, color: Colors.grey[700])),
                  if (result.userConditions.isNotEmpty) ...[
                    const SizedBox(height: 6),
                    Text(
                      'Based on: ${result.userConditions.take(3).join(', ')}',
                      style: TextStyle(
                          fontSize: 11,
                          color: Colors.grey[600],
                          fontStyle: FontStyle.italic),
                    ),
                  ],
                ],
              ),
            ),
          ]),
          // Score bar
          const SizedBox(height: 12),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: score / 100,
              backgroundColor: Colors.grey[200],
              valueColor: AlwaysStoppedAnimation<Color>(color),
              minHeight: 8,
            ),
          ),
          const SizedBox(height: 4),
          Row(children: [
            Text('0 — Dangerous', style: TextStyle(fontSize: 10, color: Colors.grey[500])),
            const Spacer(),
            Text('100 — Safe', style: TextStyle(fontSize: 10, color: Colors.grey[500])),
          ]),
        ],
      ),
    );
  }
}

// ── User Health Context Card ──────────────────────────────────────────────────

class _UserContextCard extends StatelessWidget {
  final FoodScanResult result;
  const _UserContextCard({required this.result});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.primaryContainer,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Your Health Values Used',
              style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 13,
                  color: Theme.of(context).colorScheme.onPrimaryContainer)),
          const SizedBox(height: 8),
          Wrap(
            spacing: 16, runSpacing: 6,
            children: [
              if (result.userBp != null)
                _ContextChip(label: 'BP', value: result.userBp!),
              if (result.userSugar != null)
                _ContextChip(
                    label: 'Fasting Sugar',
                    value: '${result.userSugar!.toStringAsFixed(0)} mg/dL'),
              if (result.userBmi != null)
                _ContextChip(
                    label: 'BMI',
                    value: result.userBmi!.toStringAsFixed(1)),
            ],
          ),
        ],
      ),
    );
  }
}

class _ContextChip extends StatelessWidget {
  final String label;
  final String value;
  const _ContextChip({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: TextStyle(fontSize: 10, color: Colors.grey[600])),
        Text(value,
            style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold)),
      ],
    );
  }
}

// ── Critical Allergen Banner ──────────────────────────────────────────────────

class _CriticalAllergenBanner extends StatelessWidget {
  final List<dynamic> alerts;
  const _CriticalAllergenBanner({required this.alerts});

  @override
  Widget build(BuildContext context) {
    final critical = alerts
        .where((a) => (a as Map)['severity'] == 'Severe')
        .map((a) => (a as Map)['allergen'] as String)
        .toList();
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.red[50],
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.red[300]!, width: 2),
      ),
      child: Row(children: [
        const Icon(Icons.dangerous, color: Colors.red, size: 28),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('CRITICAL ALLERGEN DETECTED',
                  style: TextStyle(
                      color: Colors.red,
                      fontWeight: FontWeight.black,
                      fontSize: 13)),
              const SizedBox(height: 3),
              Text(
                'Contains: ${critical.join(', ')}. DO NOT consume.',
                style: const TextStyle(fontSize: 13, color: Colors.red),
              ),
            ],
          ),
        ),
      ]),
    );
  }
}
