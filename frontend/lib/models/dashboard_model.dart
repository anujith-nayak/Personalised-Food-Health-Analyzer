import 'user_model.dart';
import 'health_profile_model.dart';

class DashboardModel {
  final UserModel user;
  final HealthProfileModel? healthProfile;
  final List<String> currentHealthStatuses;
  final List<String> foodRestrictions;
  final int profileCompletion;

  const DashboardModel({
    required this.user,
    this.healthProfile,
    required this.currentHealthStatuses,
    required this.foodRestrictions,
    required this.profileCompletion,
  });

  factory DashboardModel.fromJson(Map<String, dynamic> j) => DashboardModel(
        user: UserModel.fromJson(j['user'] as Map<String, dynamic>),
        healthProfile: j['health_profile'] != null
            ? HealthProfileModel.fromJson(j['health_profile'] as Map<String, dynamic>)
            : null,
        currentHealthStatuses: List<String>.from(j['current_health_statuses'] as List),
        foodRestrictions:      List<String>.from(j['food_restrictions'] as List),
        profileCompletion:     j['profile_completion'] as int,
      );
}
