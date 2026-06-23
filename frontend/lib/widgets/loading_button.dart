import 'package:flutter/material.dart';

class LoadingButton extends StatelessWidget {
  final bool loading;
  final String label;
  final VoidCallback? onPressed;

  const LoadingButton({
    super.key,
    required this.loading,
    required this.label,
    this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      height: 52,
      child: FilledButton(
        onPressed: loading ? null : onPressed,
        child: loading
            ? const SizedBox(
                width: 22, height: 22,
                child: CircularProgressIndicator(strokeWidth: 2.5, color: Colors.white),
              )
            : Text(label, style: const TextStyle(fontSize: 16)),
      ),
    );
  }
}
