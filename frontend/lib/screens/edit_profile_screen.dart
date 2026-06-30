import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/dashboard_provider.dart';
import '../constants/app_constants.dart';
import '../widgets/loading_button.dart';
import '../widgets/error_box.dart';
import '../models/dashboard_model.dart';

class EditProfileScreen extends StatefulWidget {
  const EditProfileScreen({super.key});

  @override
  State<EditProfileScreen> createState() => _EditProfileScreenState();
}

class _EditProfileScreenState extends State<EditProfileScreen> {
  // ── Tab controller ────────────────────────────────────────────────────────
  int _tab = 0;

  // ── Profile fields ────────────────────────────────────────────────────────
  final _profileFormKey = GlobalKey<FormState>();
  final _weightCtrl = TextEditingController();
  final _heightCtrl = TextEditingController();
  final _ageCtrl    = TextEditingController();
  String? _foodPref;

  // ── Health condition fields ───────────────────────────────────────────────
  final Set<String> _conditions = {};
  String _bpStatus    = 'normal';
  final _systolicCtrl  = TextEditingController();
  final _diastolicCtrl = TextEditingController();
  String _sugarStatus  = 'normal';
  final _fastingCtrl   = TextEditingController();
  final _postMealCtrl  = TextEditingController();
  String _thyroidType  = 'hypothyroidism';
  bool? _pcosDiagnosed;
  bool? _pcodDiagnosed;

  // ── Current health status ─────────────────────────────────────────────────
  final Set<String> _statuses = {};

  bool _initialized = false;
  bool _saving      = false;

  @override
  void dispose() {
    for (final c in [
      _weightCtrl, _heightCtrl, _ageCtrl,
      _systolicCtrl, _diastolicCtrl, _fastingCtrl, _postMealCtrl,
    ]) c.dispose();
    super.dispose();
  }

  void _initFromDashboard(DashboardModel d) {
    if (_initialized) return;
    _initialized = true;

    // Profile
    _weightCtrl.text = d.user.weight.toString();
    _heightCtrl.text = d.user.height.toString();
    _ageCtrl.text    = d.user.age.toString();
    _foodPref        = d.user.foodPreference;

    // Health conditions
    final p = d.healthProfile;
    if (p != null) {
      if (p.hypertension)  _conditions.add('Hypertension (BP)');
      if (p.diabetes)      _conditions.add('Diabetes');
      if (p.pcos)          _conditions.add('PCOS');
      if (p.pcod)          _conditions.add('PCOD');
      if (p.thyroid)       _conditions.add('Thyroid');
      if (p.heartDisease)  _conditions.add('Heart Disease');
      if (p.kidneyDisease) _conditions.add('Kidney Disease');
      if (p.obesity)       _conditions.add('Obesity');
      if (p.none)          _conditions.add('None');

      _bpStatus         = p.bpStatus    ?? 'normal';
      _systolicCtrl.text  = p.systolic?.toString()  ?? '';
      _diastolicCtrl.text = p.diastolic?.toString() ?? '';
      _sugarStatus      = p.sugarStatus ?? 'normal';
      _fastingCtrl.text   = p.fastingSugar?.toString()  ?? '';
      _postMealCtrl.text  = p.postMealSugar?.toString() ?? '';
      _thyroidType      = p.thyroidType ?? 'hypothyroidism';
      _pcosDiagnosed    = p.pcosDiagnosed;
      _pcodDiagnosed    = p.pcodDiagnosed;
    }

    // Current statuses
    _statuses.addAll(d.currentHealthStatuses);
  }

  // ── Save profile tab ──────────────────────────────────────────────────────
  Future<void> _saveProfile() async {
    if (!_profileFormKey.currentState!.validate()) return;
    setState(() => _saving = true);
    final ok = await context.read<DashboardProvider>().updateProfile({
      'weight':          double.tryParse(_weightCtrl.text),
      'height':          double.tryParse(_heightCtrl.text),
      'age':             int.tryParse(_ageCtrl.text),
      'food_preference': _foodPref,
    });
    if (mounted) {
      setState(() => _saving = false);
      if (ok) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Profile updated successfully')),
        );
      }
    }
  }

  // ── Save health + status tab ──────────────────────────────────────────────
  Future<void> _saveHealth() async {
    setState(() => _saving = true);

    final hasHypertension = _conditions.contains('Hypertension (BP)');
    final hasDiabetes     = _conditions.contains('Diabetes');
    final hasThyroid      = _conditions.contains('Thyroid');
    final hasPcos         = _conditions.contains('PCOS');
    final hasPcod         = _conditions.contains('PCOD');

    final payload = <String, dynamic>{
      'hypertension':   hasHypertension,
      'diabetes':       hasDiabetes,
      'thyroid':        hasThyroid,
      'pcos':           hasPcos,
      'pcod':           hasPcod,
      'heart_disease':  _conditions.contains('Heart Disease'),
      'kidney_disease': _conditions.contains('Kidney Disease'),
      'obesity':        _conditions.contains('Obesity'),
      'none':           _conditions.contains('None'),
      'current_health_statuses': _statuses.toList(),
    };

    if (hasHypertension) {
      payload['bp_status'] = _bpStatus;
      if (_systolicCtrl.text.isNotEmpty)
        payload['systolic'] = int.tryParse(_systolicCtrl.text);
      if (_diastolicCtrl.text.isNotEmpty)
        payload['diastolic'] = int.tryParse(_diastolicCtrl.text);
    }
    if (hasDiabetes) {
      payload['sugar_status'] = _sugarStatus;
      if (_fastingCtrl.text.isNotEmpty)
        payload['fasting_sugar'] = double.tryParse(_fastingCtrl.text);
      if (_postMealCtrl.text.isNotEmpty)
        payload['post_meal_sugar'] = double.tryParse(_postMealCtrl.text);
    }
    if (hasThyroid) payload['thyroid_type'] = _thyroidType;
    if (hasPcos && _pcosDiagnosed != null) payload['pcos_diagnosed'] = _pcosDiagnosed;
    if (hasPcod && _pcodDiagnosed != null) payload['pcod_diagnosed'] = _pcodDiagnosed;

    final ok = await context.read<DashboardProvider>().updateHealthProfile(payload);
    if (mounted) {
      setState(() => _saving = false);
      if (ok) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Health profile updated successfully')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final dp = context.watch<DashboardProvider>();
    if (dp.dashboard != null) _initFromDashboard(dp.dashboard!);

    return DefaultTabController(
      length: 3,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Edit Profile'),
          bottom: TabBar(
            onTap: (i) => setState(() => _tab = i),
            tabs: const [
              Tab(icon: Icon(Icons.person_outline), text: 'Profile'),
              Tab(icon: Icon(Icons.health_and_safety_outlined), text: 'Health'),
              Tab(icon: Icon(Icons.medical_information_outlined), text: 'Status'),
            ],
          ),
        ),
        body: dp.dashboard == null
            ? const Center(child: CircularProgressIndicator())
            : _buildTab(dp),
      ),
    );
  }

  Widget _buildTab(DashboardProvider dp) {
    if (dp.error != null) {
      return Padding(
        padding: const EdgeInsets.all(16),
        child: ErrorBox(dp.error!),
      );
    }
    switch (_tab) {
      case 0: return _profileTab();
      case 1: return _healthTab();
      case 2: return _statusTab();
      default: return _profileTab();
    }
  }

  // ── Tab 0: Profile ────────────────────────────────────────────────────────
  Widget _profileTab() => SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Form(
          key: _profileFormKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              TextFormField(
                controller: _weightCtrl,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                    labelText: 'Weight (kg)',
                    prefixIcon: Icon(Icons.monitor_weight_outlined)),
                validator: (v) {
                  final n = double.tryParse(v ?? '');
                  return (n != null && n > 0) ? null : 'Valid weight required';
                },
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _heightCtrl,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                    labelText: 'Height (cm)',
                    prefixIcon: Icon(Icons.height)),
                validator: (v) {
                  final n = double.tryParse(v ?? '');
                  return (n != null && n > 0) ? null : 'Valid height required';
                },
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _ageCtrl,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                    labelText: 'Age',
                    prefixIcon: Icon(Icons.cake_outlined)),
                validator: (v) {
                  final n = int.tryParse(v ?? '');
                  return (n != null && n > 0 && n < 120)
                      ? null : 'Valid age required';
                },
              ),
              const SizedBox(height: 16),
              DropdownButtonFormField<String>(
                value: _foodPref,
                decoration: const InputDecoration(
                    labelText: 'Food Preference',
                    prefixIcon: Icon(Icons.restaurant_outlined)),
                items: AppConstants.foodPreferenceOptions
                    .map((f) => DropdownMenuItem(
                        value: AppConstants.foodPrefToApi(f), child: Text(f)))
                    .toList(),
                onChanged: (v) => setState(() => _foodPref = v),
              ),
              const SizedBox(height: 24),
              LoadingButton(
                  loading: _saving,
                  label: 'Save Profile',
                  onPressed: _saveProfile),
            ],
          ),
        ),
      );

  // ── Tab 1: Health Conditions ──────────────────────────────────────────────
  Widget _healthTab() => SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text('Health Conditions',
                style: Theme.of(context)
                    .textTheme
                    .titleLarge
                    ?.copyWith(fontWeight: FontWeight.bold)),
            const SizedBox(height: 4),
            const Text('Select all that apply'),
            const SizedBox(height: 16),
            Wrap(
              spacing: 8, runSpacing: 8,
              children: AppConstants.healthConditions.map((c) {
                final sel = _conditions.contains(c);
                return FilterChip(
                  label: Text(c),
                  selected: sel,
                  onSelected: (val) => setState(() {
                    if (c == 'None') {
                      if (_conditions.contains('None')) {
                        _conditions.remove('None'); // deselect None → re-enables all
                      } else {
                        _conditions.clear();
                        _conditions.add('None');
                      }
                    } else {
                      if (val) {
                        _conditions.remove('None');
                        _conditions.add(c);
                      } else {
                        _conditions.remove(c);
                      }
                    }
                  }),
                );
              }).toList(),
            ),

            if (_conditions.contains('Hypertension (BP)')) ...[
              const SizedBox(height: 16),
              _condCard('Hypertension Details', [
                _radioRow('BP Status', ['normal', 'low', 'high'], _bpStatus,
                    (v) => setState(() => _bpStatus = v!)),
                const SizedBox(height: 12),
                Row(children: [
                  Expanded(child: TextField(
                    controller: _systolicCtrl,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(labelText: 'Systolic'),
                  )),
                  const SizedBox(width: 12),
                  Expanded(child: TextField(
                    controller: _diastolicCtrl,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(labelText: 'Diastolic'),
                  )),
                ]),
              ]),
            ],
            if (_conditions.contains('Diabetes')) ...[
              const SizedBox(height: 16),
              _condCard('Diabetes Details', [
                _radioRow('Sugar Status', ['normal', 'low', 'high'], _sugarStatus,
                    (v) => setState(() => _sugarStatus = v!)),
                const SizedBox(height: 12),
                Row(children: [
                  Expanded(child: TextField(
                    controller: _fastingCtrl,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(labelText: 'Fasting Sugar'),
                  )),
                  const SizedBox(width: 12),
                  Expanded(child: TextField(
                    controller: _postMealCtrl,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(labelText: 'Post Meal Sugar'),
                  )),
                ]),
              ]),
            ],
            if (_conditions.contains('Thyroid')) ...[
              const SizedBox(height: 16),
              _condCard('Thyroid Details', [
                _radioRow('Type', ['hypothyroidism', 'hyperthyroidism'],
                    _thyroidType, (v) => setState(() => _thyroidType = v!)),
              ]),
            ],
            if (_conditions.contains('PCOS')) ...[
              const SizedBox(height: 16),
              _condCard('PCOS Details', [
                _yesNo('Diagnosed?', _pcosDiagnosed,
                    (v) => setState(() => _pcosDiagnosed = v)),
              ]),
            ],
            if (_conditions.contains('PCOD')) ...[
              const SizedBox(height: 16),
              _condCard('PCOD Details', [
                _yesNo('Diagnosed?', _pcodDiagnosed,
                    (v) => setState(() => _pcodDiagnosed = v)),
              ]),
            ],
            const SizedBox(height: 24),
            LoadingButton(
                loading: _saving,
                label: 'Save Health Conditions',
                onPressed: _saveHealth),
          ],
        ),
      );

  // ── Tab 2: Current Health Status ──────────────────────────────────────────
  Widget _statusTab() => SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text('Current Health Status',
                style: Theme.of(context)
                    .textTheme
                    .titleLarge
                    ?.copyWith(fontWeight: FontWeight.bold)),
            const SizedBox(height: 4),
            const Text('Select all that apply'),
            const SizedBox(height: 16),
            Wrap(
              spacing: 8, runSpacing: 8,
              children: AppConstants.currentHealthStatuses.map((s) {
                final sel = _statuses.contains(s);
                return FilterChip(
                  label: Text(s),
                  selected: sel,
                  onSelected: (val) => setState(() {
                    if (val) _statuses.add(s); else _statuses.remove(s);
                  }),
                );
              }).toList(),
            ),
            const SizedBox(height: 24),
            LoadingButton(
                loading: _saving,
                label: 'Save Health Status',
                onPressed: _saveHealth),
          ],
        ),
      );

  // ── Reusable sub-form helpers ─────────────────────────────────────────────
  Widget _condCard(String title, List<Widget> children) => Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title,
                  style: Theme.of(context)
                      .textTheme
                      .titleMedium
                      ?.copyWith(fontWeight: FontWeight.bold)),
              const SizedBox(height: 12),
              ...children,
            ],
          ),
        ),
      );

  Widget _radioRow(String label, List<String> options, String current,
      ValueChanged<String?> onChange) =>
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(fontWeight: FontWeight.w500)),
          Wrap(
            children: options.map((o) => Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Radio<String>(value: o, groupValue: current, onChanged: onChange),
                Text(o[0].toUpperCase() + o.substring(1)),
                const SizedBox(width: 8),
              ],
            )).toList(),
          ),
        ],
      );

  Widget _yesNo(String label, bool? current, ValueChanged<bool?> onChange) =>
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(fontWeight: FontWeight.w500)),
          Row(children: [
            Radio<bool>(value: true, groupValue: current, onChanged: onChange),
            const Text('Yes'),
            const SizedBox(width: 16),
            Radio<bool>(value: false, groupValue: current, onChanged: onChange),
            const Text('No'),
          ]),
        ],
      );
}
