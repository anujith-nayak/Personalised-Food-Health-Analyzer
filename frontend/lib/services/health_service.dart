import 'api_client.dart';
import '../models/health_profile_model.dart';

class HealthService {
  final _api = ApiClient.instance;

  Future<HealthProfileModel> submitHealthProfile(Map<String, dynamic> data) async {
    final res = await _api.post('/health-profile', data, auth: true);
    return HealthProfileModel.fromJson(res);
  }

  Future<HealthProfileModel> updateHealthProfile(Map<String, dynamic> data) async {
    final res = await _api.put('/health-profile', data);
    return HealthProfileModel.fromJson(res);
  }
}
