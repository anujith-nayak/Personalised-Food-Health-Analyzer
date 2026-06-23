import 'api_client.dart';

class AuthService {
  final _api = ApiClient.instance;

  Future<void> register({
    required String name,
    required String email,
    required String password,
    required int age,
    required String gender,
    required double height,
    required double weight,
    required String foodPreference,
  }) async {
    final data = await _api.post('/auth/register', {
      'name': name,
      'email': email,
      'password': password,
      'age': age,
      'gender': gender.toLowerCase(),
      'height': height,
      'weight': weight,
      'food_preference': foodPreference,
    });
    await _api.saveTokens(data['access_token'], data['refresh_token']);
  }

  Future<void> login(String email, String password) async {
    final data = await _api.post('/auth/login', {
      'email': email,
      'password': password,
    });
    await _api.saveTokens(data['access_token'], data['refresh_token']);
  }

  Future<void> logout() => _api.clearTokens();

  Future<bool> isLoggedIn() => _api.hasToken();
}
