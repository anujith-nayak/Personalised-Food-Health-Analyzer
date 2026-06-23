import 'package:flutter/material.dart';
import '../services/dashboard_service.dart';
import '../models/dashboard_model.dart';

/// Holds dashboard data and manages loading/error state.
class DashboardProvider extends ChangeNotifier {
  final _service = DashboardService();

  DashboardModel? _dashboard;
  bool _loading = false;
  String? _error;

  DashboardModel? get dashboard => _dashboard;
  bool get loading => _loading;
  String? get error => _error;

  Future<void> load() async {
    _loading = true;
    _error = null;
    notifyListeners();
    try {
      _dashboard = await _service.getDashboard();
    } catch (e) {
      _error = e.toString().replaceAll('Exception: ', '');
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  Future<bool> updateProfile(Map<String, dynamic> data) async {
    try {
      await _service.updateProfile(data);
      await load(); // Refresh dashboard data
      return true;
    } catch (e) {
      _error = e.toString().replaceAll('Exception: ', '');
      notifyListeners();
      return false;
    }
  }

  Future<bool> updateHealthProfile(Map<String, dynamic> data) async {
    try {
      await _service.updateHealthProfile(data);
      await load();
      return true;
    } catch (e) {
      _error = e.toString().replaceAll('Exception: ', '');
      notifyListeners();
      return false;
    }
  }

  void clear() {
    _dashboard = null;
    _error = null;
    notifyListeners();
  }
}
