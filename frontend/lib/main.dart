import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'constants/app_theme.dart';
import 'providers/auth_provider.dart';
import 'providers/dashboard_provider.dart';
import 'providers/health_provider.dart';
import 'screens/splash_screen.dart';
import 'screens/login_screen.dart';
import 'screens/register_screen.dart';
import 'screens/bmi_result_screen.dart';
import 'screens/health_assessment_screen.dart';
import 'screens/dashboard_screen.dart';
import 'screens/edit_profile_screen.dart';
import 'screens/scan_selection_screen.dart';

void main() {
  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AuthProvider()),
        ChangeNotifierProvider(create: (_) => DashboardProvider()),
        ChangeNotifierProvider(create: (_) => HealthProvider()),
      ],
      child: const FoodHealthApp(),
    ),
  );
}

class FoodHealthApp extends StatelessWidget {
  const FoodHealthApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'FoodHealth AI',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      darkTheme: AppTheme.dark,
      themeMode: ThemeMode.system,
      initialRoute: '/',
      routes: {
        '/':                  (_) => const SplashScreen(),
        '/login':             (_) => const LoginScreen(),
        '/register':          (_) => const RegisterScreen(),
        '/bmi-result':        (_) => const BmiResultScreen(),       // NEW
        '/health-assessment': (_) => const HealthAssessmentScreen(),
        '/dashboard':         (_) => const DashboardScreen(),
        '/edit-profile':      (_) => const EditProfileScreen(),
        '/scan':              (_) => const ScanSelectionScreen(),
      },
    );
  }
}
