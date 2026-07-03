import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'dart:convert';
import '../constants/app_constants.dart';

class FoodScanService {
  final _storage = const FlutterSecureStorage();

  Future<Map<String, dynamic>> analyzeFoodLabel(File imageFile) async {
    final token = await _storage.read(key: AppConstants.accessTokenKey);
    final uri   = Uri.parse('${AppConstants.baseUrl}/food/analyze-food-label');

    final request = http.MultipartRequest('POST', uri)
      ..headers['Authorization'] = 'Bearer $token'
      ..files.add(await http.MultipartFile.fromPath('file', imageFile.path));

    final streamed = await request.send();
    final response = await http.Response.fromStream(streamed);

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      final body = jsonDecode(response.body);
      throw Exception(body['detail'] ?? 'Analysis failed');
    }
  }
}
