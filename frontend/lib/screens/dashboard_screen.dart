import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../providers/dashboard_provider.dart';
import '../models/dashboard_model.dart';
import '../widgets/info_card.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  @override
  void initState() {
    super.initState();
    // Load dashboard data when screen opens
    Future.microtask(() => context.read<DashboardProvider>().load());
  }

  @override
  Widget build(BuildContext context) {
    final dp = context.watch<DashboardProvider>();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Dashboard'),
        actions: [
          IconButton(
            icon: const Icon(Icons.qr_code_scanner),
            tooltip: 'Scan Food',
            onPressed: () => Navigator.pushNamed(context, '/scan'),
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Logout',
            onPressed: () async {
              context.read<DashboardProvider>().clear();
              await context.read<AuthProvider>().logout();
              if (mounted) Navigator.pushReplacementNamed(context, '/login');
            },
          ),
        ],
      ),
      body: Builder(builder: (_) {
        if (dp.loading) {
          return const Center(child: CircularProgressIndicator());
        }
        if (dp.error != null) {
          return Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.error_outline, size: 48),
                const SizedBox(height: 12),
                Text(dp.error!),
                const SizedBox(height: 16),
                FilledButton(
                    onPressed: () => dp.load(),
                    child: const Text('Retry')),
              ],
            ),
          );
        }
        if (dp.dashboard == null) return const SizedBox();
        return _DashboardBody(data: dp.dashboard!);
      }),
    );
  }
}

class _DashboardBody extends StatelessWidget {
  final DashboardModel data;
  const _DashboardBody({required this.data});

  @override
  Widget build(BuildContext context) {
    final user    = data.user;
    final profile = data.healthProfile;

    return RefreshIndicator(
      onRefresh: () => context.read<DashboardProvider>().load(),
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // ── Profile Card ─────────────────────────────────────────────────
          InfoCard(
            title: 'Profile',
            icon: Icons.person,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _row('Name', user.name),
                _row('Age', '${user.age} years'),
                _row('Gender', user.gender),
                _row('Height', '${user.height} cm'),
                _row('Weight', '${user.weight} kg'),
                _row('Food Preference', user.foodPreference),
              ],
            ),
          ),
          const SizedBox(height: 12),

          // ── BMI Card ─────────────────────────────────────────────────────
          InfoCard(
            title: 'BMI',
            icon: Icons.monitor_weight,
            child: user.bmiScore != null
                ? Row(children: [
                    Text(
                      user.bmiScore!.toStringAsFixed(1),
                      style: Theme.of(context).textTheme.displaySmall?.copyWith(
                            color: Theme.of(context).colorScheme.primary,
                            fontWeight: FontWeight.bold,
                          ),
                    ),
                    const SizedBox(width: 16),
                    _bmiChip(context, user.bmiCategory ?? ''),
                  ])
                : const Text('BMI not available'),
          ),
          const SizedBox(height: 12),

          // ── Health Conditions ────────────────────────────────────────────
          if (profile != null)
            InfoCard(
              title: 'Health Conditions',
              icon: Icons.health_and_safety,
              child: profile.activeConditions.isEmpty
                  ? const Text('No conditions selected')
                  : Wrap(
                      spacing: 8, runSpacing: 8,
                      children: profile.activeConditions
                          .map((c) => Chip(label: Text(c)))
                          .toList(),
                    ),
            ),
          if (profile != null) const SizedBox(height: 12),

          // ── Current Health Status ────────────────────────────────────────
          InfoCard(
            title: 'Current Health Status',
            icon: Icons.medical_information,
            child: data.currentHealthStatuses.isEmpty
                ? const Text('No status recorded')
                : Wrap(
                    spacing: 8, runSpacing: 8,
                    children: data.currentHealthStatuses
                        .map((s) => Chip(label: Text(s)))
                        .toList(),
                  ),
          ),
          const SizedBox(height: 12),

          // ── Food Restrictions ────────────────────────────────────────────
          InfoCard(
            title: 'Food Restrictions',
            icon: Icons.no_food,
            child: data.foodRestrictions.isEmpty
                ? const Text('No restrictions')
                : Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: data.foodRestrictions
                        .map((r) => Padding(
                              padding: const EdgeInsets.symmetric(vertical: 3),
                              child: Row(children: [
                                Icon(Icons.block,
                                    size: 16,
                                    color: Theme.of(context).colorScheme.error),
                                const SizedBox(width: 8),
                                Expanded(child: Text(r)),
                              ]),
                            ))
                        .toList(),
                  ),
          ),
          const SizedBox(height: 12),

          // ── Profile Completion ───────────────────────────────────────────
          InfoCard(
            title: 'Profile Completion',
            icon: Icons.task_alt,
            child: Row(children: [
              Expanded(
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(4),
                  child: LinearProgressIndicator(
                    value: data.profileCompletion / 100,
                    minHeight: 10,
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Text('${data.profileCompletion}%',
                  style: const TextStyle(fontWeight: FontWeight.bold)),
            ]),
          ),
          const SizedBox(height: 24),

          // ── Action Buttons ───────────────────────────────────────────────
          OutlinedButton.icon(
            icon: const Icon(Icons.edit),
            label: const Text('Edit Profile'),
            onPressed: () async {
              await Navigator.pushNamed(context, '/edit-profile');
              // Refresh dashboard data when returning from edit
              if (context.mounted) context.read<DashboardProvider>().load();
            },
          ),
          const SizedBox(height: 12),
          FilledButton.icon(
            icon: const Icon(Icons.qr_code_scanner),
            label: const Text('Scan Food'),
            onPressed: () => Navigator.pushNamed(context, '/scan'),
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }

  Widget _row(String label, String value) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(children: [
          SizedBox(
              width: 130,
              child: Text(label,
                  style: const TextStyle(fontWeight: FontWeight.w500))),
          Expanded(child: Text(value)),
        ]),
      );

  Widget _bmiChip(BuildContext context, String category) {
    final colors = {
      'Underweight': Colors.blue,
      'Normal Weight': Colors.green,
      'Overweight': Colors.orange,
      'Obese': Colors.red,
    };
    final color = colors[category] ?? Colors.grey;
    return Chip(
      label: Text(category,
          style: const TextStyle(color: Colors.white, fontSize: 12)),
      backgroundColor: color,
    );
  }
}
