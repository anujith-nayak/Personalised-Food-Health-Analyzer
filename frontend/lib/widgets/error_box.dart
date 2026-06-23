import 'package:flutter/material.dart';

class ErrorBox extends StatelessWidget {
  final String message;
  const ErrorBox(this.message, {super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.errorContainer,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(children: [
        Icon(Icons.error_outline,
            color: Theme.of(context).colorScheme.onErrorContainer, size: 20),
        const SizedBox(width: 8),
        Expanded(
          child: Text(message,
              style: TextStyle(
                  color: Theme.of(context).colorScheme.onErrorContainer)),
        ),
      ]),
    );
  }
}
