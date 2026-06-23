import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/dashboard_provider.dart';

/// Shown after registration — displays calculated BMI before Health Assessment.
class BmiResultScreen extends StatefulWidget {
  const BmiResultScreen({super.key});

  @override
  State<BmiResultScreen> createState() => _BmiResultScreenState();
}

class _BmiResultScreenState extends State<BmiResultScreen> {
  @override
  void initState() {
    super.initState();
    Future.microtask(() => context.read<DashboardProvider>().load());
  }

  @override
  Widget build(BuildContext context) {
    final dp   = context.watch<DashboardProvider>();
    final user = dp.dashboard?.user;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Your BMI'),
        automaticallyImplyLeading: false,
      ),
      body: dp.loading
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.all(32),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const SizedBox(height: 16),
                  Icon(
                    Icons.monitor_weight_outlined,
                    size: 80,
                    color: Theme.of(context).colorScheme.primary,
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'BMI Calculated',
                    textAlign: TextAlign.center,
                    style: Theme.of(context)
                        .textTheme
                        .headlineMedium
                        ?.copyWith(fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 24),

                  // ── BMI Score box ────────────────────────────────────────
                  Container(
                    padding: const EdgeInsets.symmetric(vertical: 28, horizontal: 24),
                    decoration: BoxDecoration(
                      color: Theme.of(context).colorScheme.primaryContainer,
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: Column(
                      children: [
                        Text(
                          user?.bmiScore?.toStringAsFixed(1) ?? '--',
                          textAlign: TextAlign.center,
                          style: Theme.of(context)
                              .textTheme
                              .displayLarge
                              ?.copyWith(
                                fontWeight: FontWeight.bold,
                                color: Theme.of(context)
                                    .colorScheme
                                    .onPrimaryContainer,
                              ),
                        ),
                        const SizedBox(height: 12),
                        if (user?.bmiCategory != null)
                          _buildCategoryBadge(user!.bmiCategory!),
                      ],
                    ),
                  ),
                  const SizedBox(height: 20),

                  // ── BMI reference scale ──────────────────────────────────
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('BMI Scale',
                              style: Theme.of(context)
                                  .textTheme
                                  .titleSmall
                                  ?.copyWith(fontWeight: FontWeight.bold)),
                          const SizedBox(height: 10),
                          _scaleRow('< 18.5',       'Underweight',   Colors.blue),
                          _scaleRow('18.5 – 24.9',  'Normal Weight', Colors.green),
                          _scaleRow('25 – 29.9',    'Overweight',    Colors.orange),
                          _scaleRow('≥ 30',         'Obese',         Colors.red),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 24),

                  Text(
                    'Next: Tell us about your health conditions',
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 16),

                  FilledButton(
                    onPressed: () => Navigator.pushReplacementNamed(
                        context, '/health-assessment'),
                    child: const Text('Continue to Health Assessment'),
                  ),
                ],
              ),
            ),
    );
  }

  Widget _buildCategoryBadge(String category) {
    final colorMap = <String, Color>{
      'Underweight':   Colors.blue,
      'Normal Weight': Colors.green,
      'Overweight':    Colors.orange,
      'Obese':         Colors.red,
    };
    final color = colorMap[category] ?? Colors.grey;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(24),
      ),
      child: Text(
        category,
        style: const TextStyle(
          color: Colors.white,
          fontWeight: FontWeight.bold,
          fontSize: 16,
        ),
      ),
    );
  }

  Widget _scaleRow(String range, String label, Color color) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(children: [
          Container(
            width: 12, height: 12,
            decoration: BoxDecoration(color: color, shape: BoxShape.circle),
          ),
          const SizedBox(width: 10),
          SizedBox(width: 90, child: Text(range, style: const TextStyle(fontSize: 13))),
          Text(label,
              style: TextStyle(
                  fontSize: 13, color: color, fontWeight: FontWeight.w600)),
        ]),
      );
}
