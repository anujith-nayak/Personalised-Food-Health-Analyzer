import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    _navigate();
  }

  Future<void> _navigate() async {
    await Future.delayed(const Duration(seconds: 3));
    if (!mounted) return;
    final isAuth = await context.read<AuthProvider>().isLoggedIn();
    if (!mounted) return;
    Navigator.pushReplacementNamed(
        context, isAuth ? '/dashboard' : '/login');
  }

  @override
  Widget build(BuildContext context) {
    final color = Theme.of(context).colorScheme;
    return Scaffold(
      backgroundColor: color.primary,
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.restaurant_menu, size: 96, color: color.onPrimary),
            const SizedBox(height: 24),
            Text(
              'FoodHealth AI',
              style: Theme.of(context)
                  .textTheme
                  .headlineLarge
                  ?.copyWith(color: color.onPrimary, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Text(
              'Your personalized health companion',
              style: Theme.of(context)
                  .textTheme
                  .bodyLarge
                  ?.copyWith(color: color.onPrimary.withOpacity(0.85)),
            ),
            const SizedBox(height: 48),
            CircularProgressIndicator(
                valueColor: AlwaysStoppedAnimation<Color>(color.onPrimary)),
          ],
        ),
      ),
    );
  }
}
