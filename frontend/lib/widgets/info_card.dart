import 'package:flutter/material.dart';

/// Reusable card used throughout the dashboard.
class InfoCard extends StatelessWidget {
  final String title;
  final IconData icon;
  final Widget child;

  const InfoCard({
    super.key,
    required this.title,
    required this.icon,
    required this.child,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              Icon(icon, color: Theme.of(context).colorScheme.primary, size: 20),
              const SizedBox(width: 8),
              Text(title,
                  style: Theme.of(context)
                      .textTheme
                      .titleMedium
                      ?.copyWith(fontWeight: FontWeight.bold)),
            ]),
            const Divider(height: 20),
            child,
          ],
        ),
      ),
    );
  }
}
