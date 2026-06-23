import 'package:flutter/material.dart';
import '../services/auth_service.dart';

/// Manages authentication state across the app.
class AuthProvider extends ChangeNotifier {
  final _service = AuthService();

  bool _loading = false;
  String? _error;

  bool get loading => _loading;
  String? get error => _error;

  Future<bool> isLoggedIn() => _service.isLoggedIn();

  Future<bool> login(String email, String password) async {
    _setLoading(true);
    try {
      await _service.login(email, password);
      _error = null;
      return true;
    } catch (e) {
      _error = e.toString().replaceAll('Exception: ', '');
      return false;
    } finally {
      _setLoading(false);
    }
  }

  Future<bool> register({
    required String name,
    required String email,
    required String password,
    required int age,
    required String gender,
    required double height,
    required double weight,
    required String foodPreference,
  }) async {
    _setLoading(true);
    try {
      await _service.register(
        name: name, email: email, password: password,
        age: age, gender: gender, height: height,
        weight: weight, foodPreference: foodPreference,
      );
      _error = null;
      return true;
    } catch (e) {
      _error = e.toString().replaceAll('Exception: ', '');
      return false;
    } finally {
      _setLoading(false);
    }
  }

  Future<void> logout() async {
    await _service.logout();
    notifyListeners();
  }

  void _setLoading(bool val) {
    _loading = val;
    notifyListeners();
  }

  void clearError() {
    _error = null;
    notifyListeners();
  }
}
