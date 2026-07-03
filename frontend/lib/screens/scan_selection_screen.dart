import 'package:flutter/material.dart';
import 'food_scan_screen.dart';

class ScanSelectionScreen extends StatelessWidget {
  const ScanSelectionScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Food Scanner')),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text('Choose Scan Type',
                style: Theme.of(context)
                    .textTheme
                    .headlineSmall
                    ?.copyWith(fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            Text(
              'Scan a packaged food label to check if it\'s safe for your health.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 32),

            // Option 1 — Packaged Food Label (WORKING)
            _ScanCard(
              icon: Icons.qr_code_scanner,
              title: 'Scan Packaged Food Label',
              badge: 'Available',
              badgeColor: Colors.green,
              description:
                  'Point your camera at any packaged food label. '
                  'We\'ll extract ingredients and nutrition info and check them '
                  'against your health profile.',
              buttonLabel: 'Open Scanner',
              onTap: () => Navigator.push(
                context,
                MaterialPageRoute(
                    builder: (_) => const FoodScanScreen()),
              ),
            ),
            const SizedBox(height: 16),

            // Option 2 — Live Food Scan (Phase 2)
            _ScanCard(
              icon: Icons.camera_alt,
              title: 'Live Food Recognition',
              badge: 'Phase 2',
              badgeColor: Colors.amber[700]!,
              description:
                  'Capture a real food item using your camera. '
                  'AI will identify the food and give instant health recommendations. '
                  'Coming in Phase 2 with ML integration.',
              buttonLabel: 'Coming Soon',
              onTap: () => _showComingSoon(context),
            ),
          ],
        ),
      ),
    );
  }

  void _showComingSoon(BuildContext context) {
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        icon: const Icon(Icons.rocket_launch, size: 48),
        title: const Text('Coming in Phase 2'),
        content: const Text(
          'Live food recognition with AI/ML models will be available in Phase 2.',
        ),
        actions: [
          FilledButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Got it')),
        ],
      ),
    );
  }
}

class _ScanCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String badge;
  final Color badgeColor;
  final String description;
  final String buttonLabel;
  final VoidCallback onTap;

  const _ScanCard({
    required this.icon,
    required this.title,
    required this.badge,
    required this.badgeColor,
    required this.description,
    required this.buttonLabel,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: cs.primaryContainer,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(icon, size: 28, color: cs.onPrimaryContainer),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(title,
                    style: Theme.of(context)
                        .textTheme
                        .titleMedium
                        ?.copyWith(fontWeight: FontWeight.bold)),
              ),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: badgeColor.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: badgeColor.withOpacity(0.4)),
                ),
                child: Text(badge,
                    style: TextStyle(
                        color: badgeColor,
                        fontSize: 11,
                        fontWeight: FontWeight.bold)),
              ),
            ]),
            const SizedBox(height: 12),
            Text(description,
                style: Theme.of(context)
                    .textTheme
                    .bodySmall
                    ?.copyWith(color: Colors.grey[600])),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                icon: Icon(icon, size: 18),
                label: Text(buttonLabel),
                onPressed: onTap,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
