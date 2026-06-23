import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../constants/app_constants.dart';

/// Central HTTP client.
/// All API calls go through this class so token injection is in one place.
class ApiClient {
  ApiClient._();
  static final ApiClient instance = ApiClient._();

  final _storage = const FlutterSecureStorage();

  // ── Helpers ──────────────────────────────────────────────────────────────

  Future<Map<String, String>> _headers({bool auth = true}) async {
    final headers = {'Content-Type': 'application/json'};
    if (auth) {
      final token = await _storage.read(key: AppConstants.accessTokenKey);
      if (token != null) headers['Authorization'] = 'Bearer $token';
    }
    return headers;
  }

  Uri _uri(String path) => Uri.parse('${AppConstants.baseUrl}$path');

  /// Throws a descriptive exception on non-2xx responses.
  void _check(http.Response res) {
    if (res.statusCode < 200 || res.statusCode >= 300) {
      String message = 'Request failed (${res.statusCode})';
      try {
        final body = jsonDecode(res.body);
        message = body['detail'] ?? message;
      } catch (_) {}
      throw Exception(message);
    }
  }

  // ── Public Methods ────────────────────────────────────────────────────────

  Future<Map<String, dynamic>> post(String path, Map<String, dynamic> body,
      {bool auth = false}) async {
    final res = await http.post(
      _uri(path),
      headers: await _headers(auth: auth),
      body: jsonEncode(body),
    );
    _check(res);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> get(String path) async {
    final res = await http.get(_uri(path), headers: await _headers());
    _check(res);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> put(String path, Map<String, dynamic> body) async {
    final res = await http.put(
      _uri(path),
      headers: await _headers(),
      body: jsonEncode(body),
    );
    _check(res);
    return jsonDecode(res.body) as Map<String, dynamic>;
  }

  // ── Token Storage ─────────────────────────────────────────────────────────

  Future<void> saveTokens(String access, String refresh) async {
    await _storage.write(key: AppConstants.accessTokenKey, value: access);
    await _storage.write(key: AppConstants.refreshTokenKey, value: refresh);
  }

  Future<void> clearTokens() async {
    await _storage.delete(key: AppConstants.accessTokenKey);
    await _storage.delete(key: AppConstants.refreshTokenKey);
  }

  Future<bool> hasToken() async {
    final t = await _storage.read(key: AppConstants.accessTokenKey);
    return t != null;
  }
}
