import 'api_client.dart';
import '../models/dashboard_model.dart';

class DashboardService {
  final _api = ApiClient.instance;

  Future<DashboardModel> getDashboard() async {
    final res = await _api.get('/dashboard');
    return DashboardModel.fromJson(res);
  }

  Future<void> updateProfile(Map<String, dynamic> data) async {
    await _api.put('/profile', data);
  }

  Future<void> updateHealthProfile(Map<String, dynamic> data) async {
    await _api.put('/health-profile', data);
  }
}
