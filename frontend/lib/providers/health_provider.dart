import 'package:flutter/material.dart';
import '../services/health_service.dart';

/// Manages health assessment submission state.
class HealthProvider extends ChangeNotifier {
  final _service = HealthService();

  bool _loading = false;
  String? _error;

  bool get loading => _loading;
  String? get error => _error;

  Future<bool> submitHealthProfile(Map<String, dynamic> data) async {
    _loading = true;
    _error = null;
    notifyListeners();
    try {
      await _service.submitHealthProfile(data);
      return true;
    } catch (e) {
      _error = e.toString().replaceAll('Exception: ', '');
      return false;
    } finally {
      _loading = false;
      notifyListeners();
    }
  }
}
