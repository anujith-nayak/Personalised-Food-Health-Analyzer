import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../constants/app_constants.dart';
import '../widgets/loading_button.dart';
import '../widgets/error_box.dart';

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _formKey        = GlobalKey<FormState>();
  final _nameCtrl       = TextEditingController();
  final _emailCtrl      = TextEditingController();
  final _passCtrl       = TextEditingController();
  final _confirmCtrl    = TextEditingController();
  final _ageCtrl        = TextEditingController();
  final _heightCtrl     = TextEditingController();
  final _weightCtrl     = TextEditingController();
  String _gender        = 'Male';
  String _foodPref      = 'Mixed';
  bool _obscure         = true;

  @override
  void dispose() {
    for (final c in [_nameCtrl, _emailCtrl, _passCtrl, _confirmCtrl,
                     _ageCtrl, _heightCtrl, _weightCtrl]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _register() async {
    if (!_formKey.currentState!.validate()) return;
    final auth = context.read<AuthProvider>();
    final ok = await auth.register(
      name:           _nameCtrl.text.trim(),
      email:          _emailCtrl.text.trim(),
      password:       _passCtrl.text,
      age:            int.parse(_ageCtrl.text.trim()),
      gender:         _gender,
      height:         double.parse(_heightCtrl.text.trim()),
      weight:         double.parse(_weightCtrl.text.trim()),
      foodPreference: AppConstants.foodPrefToApi(_foodPref),
    );
    if (ok && mounted) Navigator.pushReplacementNamed(context, '/bmi-result');
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    return Scaffold(
      appBar: AppBar(title: const Text('Create Account')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (auth.error != null) ...[
                ErrorBox(auth.error!),
                const SizedBox(height: 16),
              ],

              _label('Personal Information'),
              const SizedBox(height: 12),

              _field(_nameCtrl, 'Full Name', Icons.person_outline,
                  validator: (v) => v!.trim().isEmpty ? 'Name required' : null),
              const SizedBox(height: 12),

              _field(_emailCtrl, 'Email', Icons.email_outlined,
                  type: TextInputType.emailAddress,
                  validator: (v) => v!.contains('@') ? null : 'Valid email required'),
              const SizedBox(height: 12),

              TextFormField(
                controller: _passCtrl,
                obscureText: _obscure,
                decoration: InputDecoration(
                  labelText: 'Password',
                  prefixIcon: const Icon(Icons.lock_outline),
                  suffixIcon: IconButton(
                    icon: Icon(_obscure ? Icons.visibility_outlined : Icons.visibility_off_outlined),
                    onPressed: () => setState(() => _obscure = !_obscure),
                  ),
                ),
                validator: (v) => v!.length >= 6 ? null : 'Minimum 6 characters',
              ),
              const SizedBox(height: 12),

              TextFormField(
                controller: _confirmCtrl,
                obscureText: true,
                decoration: const InputDecoration(
                    labelText: 'Confirm Password',
                    prefixIcon: Icon(Icons.lock_outline)),
                validator: (v) =>
                    v == _passCtrl.text ? null : 'Passwords do not match',
              ),
              const SizedBox(height: 12),

              _field(_ageCtrl, 'Age', Icons.cake_outlined,
                  type: TextInputType.number,
                  validator: (v) {
                    final n = int.tryParse(v ?? '');
                    return (n != null && n > 0 && n < 120) ? null : 'Valid age required';
                  }),
              const SizedBox(height: 12),

              DropdownButtonFormField<String>(
                value: _gender,
                decoration: const InputDecoration(
                    labelText: 'Gender', prefixIcon: Icon(Icons.wc_outlined)),
                items: AppConstants.genderOptions
                    .map((g) => DropdownMenuItem(value: g, child: Text(g)))
                    .toList(),
                onChanged: (v) => setState(() => _gender = v!),
              ),
              const SizedBox(height: 12),

              _field(_heightCtrl, 'Height (cm)', Icons.height,
                  type: TextInputType.number,
                  validator: (v) {
                    final n = double.tryParse(v ?? '');
                    return (n != null && n > 50 && n < 300)
                        ? null : 'Valid height required';
                  }),
              const SizedBox(height: 12),

              _field(_weightCtrl, 'Weight (kg)', Icons.monitor_weight_outlined,
                  type: TextInputType.number,
                  validator: (v) {
                    final n = double.tryParse(v ?? '');
                    return (n != null && n > 1 && n < 500)
                        ? null : 'Valid weight required';
                  }),
              const SizedBox(height: 12),

              DropdownButtonFormField<String>(
                value: _foodPref,
                decoration: const InputDecoration(
                    labelText: 'Food Preference',
                    prefixIcon: Icon(Icons.restaurant_outlined)),
                items: AppConstants.foodPreferenceOptions
                    .map((f) => DropdownMenuItem(value: f, child: Text(f)))
                    .toList(),
                onChanged: (v) => setState(() => _foodPref = v!),
              ),
              const SizedBox(height: 24),

              LoadingButton(
                  loading: auth.loading,
                  label: 'Continue to Health Assessment',
                  onPressed: _register),
              const SizedBox(height: 12),

              TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Already have an account? Login'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _label(String text) => Text(text,
      style: Theme.of(context)
          .textTheme
          .titleMedium
          ?.copyWith(fontWeight: FontWeight.bold));

  Widget _field(
    TextEditingController ctrl,
    String label,
    IconData icon, {
    TextInputType type = TextInputType.text,
    String? Function(String?)? validator,
  }) =>
      TextFormField(
        controller: ctrl,
        keyboardType: type,
        decoration: InputDecoration(labelText: label, prefixIcon: Icon(icon)),
        validator: validator,
      );
}
