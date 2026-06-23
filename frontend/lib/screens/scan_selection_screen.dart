import 'package:flutter/material.dart';

class ScanSelectionScreen extends StatelessWidget {
  const ScanSelectionScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Food Scan')),
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
              'AI-powered scanning is coming in Phase 2.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 32),
            _ScanCard(
              icon: Icons.qr_code_scanner,
              title: 'Scan Packaged Food Label',
              description:
                  'Scan food package labels and ingredient lists to check if they suit your health conditions.',
              buttonLabel: 'Open Scanner',
            ),
            const SizedBox(height: 16),
            _ScanCard(
              icon: Icons.camera_alt,
              title: 'Live Food Scan',
              description:
                  'Point your camera at any food item to get instant health recommendations.',
              buttonLabel: 'Open Camera',
            ),
          ],
        ),
      ),
    );
  }
}

class _ScanCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String description;
  final String buttonLabel;

  const _ScanCard({
    required this.icon,
    required this.title,
    required this.description,
    required this.buttonLabel,
  });

  void _showComingSoon(BuildContext context) {
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        icon: const Icon(Icons.rocket_launch, size: 48),
        title: const Text('Coming in Phase 2'),
        content: const Text(
          'AI-powered food scanning with machine learning models will be available in Phase 2.',
        ),
        actions: [
          FilledButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Got it')),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
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
                child: Icon(icon, size: 32, color: cs.onPrimaryContainer),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Text(title,
                    style: Theme.of(context)
                        .textTheme
                        .titleMedium
                        ?.copyWith(fontWeight: FontWeight.bold)),
              ),
            ]),
            const SizedBox(height: 16),
            Text(description),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                icon: Icon(icon),
                label: Text(buttonLabel),
                onPressed: () => _showComingSoon(context),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
