import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/health_provider.dart';
import '../constants/app_constants.dart';
import '../widgets/loading_button.dart';
import '../widgets/error_box.dart';

class HealthAssessmentScreen extends StatefulWidget {
  const HealthAssessmentScreen({super.key});

  @override
  State<HealthAssessmentScreen> createState() => _HealthAssessmentScreenState();
}

class _HealthAssessmentScreenState extends State<HealthAssessmentScreen> {
  // Selected conditions
  final Set<String> _conditions = {};

  // Hypertension
  String _bpStatus = 'normal';
  final _systolicCtrl  = TextEditingController();
  final _diastolicCtrl = TextEditingController();

  // Diabetes
  String _sugarStatus = 'normal';
  final _fastingCtrl   = TextEditingController();
  final _postMealCtrl  = TextEditingController();

  // Thyroid
  String _thyroidType = 'hypothyroidism';

  // PCOS / PCOD
  bool? _pcosDiagnosed;
  bool? _pcodDiagnosed;

  // Current health status
  final Set<String> _statuses = {};

  @override
  void dispose() {
    _systolicCtrl.dispose();
    _diastolicCtrl.dispose();
    _fastingCtrl.dispose();
    _postMealCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final hasHypertension = _conditions.contains('Hypertension (BP)');
    final hasDiabetes     = _conditions.contains('Diabetes');
    final hasThyroid      = _conditions.contains('Thyroid');
    final hasPcos         = _conditions.contains('PCOS');
    final hasPcod         = _conditions.contains('PCOD');

    final payload = <String, dynamic>{
      'hypertension':  hasHypertension,
      'diabetes':      hasDiabetes,
      'thyroid':       hasThyroid,
      'pcos':          hasPcos,
      'pcod':          hasPcod,
      'heart_disease': _conditions.contains('Heart Disease'),
      'kidney_disease': _conditions.contains('Kidney Disease'),
      'obesity':       _conditions.contains('Obesity'),
      'none':          _conditions.contains('None'),
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

    final ok = await context.read<HealthProvider>().submitHealthProfile(payload);
    if (ok && mounted) Navigator.pushReplacementNamed(context, '/dashboard');
  }

  @override
  Widget build(BuildContext context) {
    final health = context.watch<HealthProvider>();
    return Scaffold(
      appBar: AppBar(title: const Text('Health Assessment')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text('Select your health conditions',
                style: Theme.of(context)
                    .textTheme
                    .titleLarge
                    ?.copyWith(fontWeight: FontWeight.bold)),
            const SizedBox(height: 4),
            const Text('Select all that apply'),
            const SizedBox(height: 16),

            // ── Condition chips ──────────────────────────────────────────────
            Wrap(
              spacing: 8, runSpacing: 8,
              children: AppConstants.healthConditions.map((c) {
                final selected = _conditions.contains(c);
                final noneActive = _conditions.contains('None') && c != 'None';
                return FilterChip(
                  label: Text(c),
                  selected: selected,
                  // Disable other chips when None is selected
                  onSelected: noneActive ? null : (val) => setState(() {
                    if (val) {
                      if (c == 'None') _conditions.clear();
                      _conditions.add(c);
                    } else {
                      _conditions.remove(c);
                    }
                  }),
                );
              }).toList(),
            ),

            // ── Condition-specific sub-forms ─────────────────────────────────
            if (_conditions.contains('Hypertension (BP)')) ...[
              const SizedBox(height: 20),
              _condCard('Hypertension Details', [
                _radioRow('BP Status', ['normal', 'low', 'high'], _bpStatus,
                    (v) => setState(() => _bpStatus = v!)),
                const SizedBox(height: 12),
                Row(children: [
                  Expanded(child: TextFormField(
                    controller: _systolicCtrl,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(labelText: 'Systolic (mmHg)'),
                  )),
                  const SizedBox(width: 12),
                  Expanded(child: TextFormField(
                    controller: _diastolicCtrl,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(labelText: 'Diastolic (mmHg)'),
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
                  Expanded(child: TextFormField(
                    controller: _fastingCtrl,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(labelText: 'Fasting Sugar'),
                  )),
                  const SizedBox(width: 12),
                  Expanded(child: TextFormField(
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
                _radioRow(
                  'Type',
                  ['hypothyroidism', 'hyperthyroidism'],
                  _thyroidType,
                  (v) => setState(() => _thyroidType = v!),
                ),
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

            // ── Current Health Status ────────────────────────────────────────
            const SizedBox(height: 24),
            Text('Current Health Status',
                style: Theme.of(context)
                    .textTheme
                    .titleLarge
                    ?.copyWith(fontWeight: FontWeight.bold)),
            const SizedBox(height: 4),
            const Text('Select all that apply'),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8, runSpacing: 8,
              children: AppConstants.currentHealthStatuses.map((s) {
                final selected = _statuses.contains(s);
                return FilterChip(
                  label: Text(s),
                  selected: selected,
                  onSelected: (val) => setState(() {
                    if (val) _statuses.add(s); else _statuses.remove(s);
                  }),
                );
              }).toList(),
            ),

            if (health.error != null) ...[
              const SizedBox(height: 16),
              ErrorBox(health.error!),
            ],
            const SizedBox(height: 24),
            LoadingButton(
              loading: health.loading,
              label: 'Save & Go to Dashboard',
              onPressed: _submit,
            ),
          ],
        ),
      ),
    );
  }

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
