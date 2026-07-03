class AppConstants {
  AppConstants._();

  static const String appName = 'FoodHealth AI';

  // Change this to your machine's IP when testing on a physical device
  // Android emulator → 10.0.2.2  (default, no change needed)
  // iOS simulator    → localhost
  // Physical device  → your local IP from `ipconfig` e.g. 192.168.1.5
  static const String baseUrl = 'http://10.0.2.2:8001'; // ← CHANGE THIS if using a physical device

  static const String accessTokenKey  = 'access_token';
  static const String refreshTokenKey = 'refresh_token';

  static const List<String> genderOptions = ['Male', 'Female', 'Other'];

  static const List<String> foodPreferenceOptions = [
    'Vegetarian',
    'Non-Vegetarian',
    'Mixed',
  ];

  static const List<String> healthConditions = [
    'Hypertension (BP)',
    'Diabetes',
    'PCOS',
    'PCOD',
    'Thyroid',
    'Heart Disease',
    'Kidney Disease',
    'Obesity',
    'None',
  ];

  static const List<String> currentHealthStatuses = [
    'Normal',
    'Fever',
    'Cold',
    'Cough',
    'Stomach Upset',
    'Vomiting',
    'Diarrhea',
    'Weakness',
    'Headache',
    'Other',
  ];

  // Maps display name → API field name
  static String foodPrefToApi(String display) =>
      display.toLowerCase().replaceAll('-', '_').replaceAll(' ', '_');
}
