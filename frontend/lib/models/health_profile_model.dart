class HealthProfileModel {
  final int id;
  final int userId;
  final bool hypertension;
  final String? bpStatus;
  final int? systolic;
  final int? diastolic;
  final bool diabetes;
  final String? sugarStatus;
  final double? fastingSugar;
  final double? postMealSugar;
  final bool thyroid;
  final String? thyroidType;
  final bool pcos;
  final bool? pcosDiagnosed;
  final bool pcod;
  final bool? pcodDiagnosed;
  final bool heartDisease;
  final bool kidneyDisease;
  final bool obesity;
  final bool none;

  const HealthProfileModel({
    required this.id,
    required this.userId,
    required this.hypertension,
    this.bpStatus,
    this.systolic,
    this.diastolic,
    required this.diabetes,
    this.sugarStatus,
    this.fastingSugar,
    this.postMealSugar,
    required this.thyroid,
    this.thyroidType,
    required this.pcos,
    this.pcosDiagnosed,
    required this.pcod,
    this.pcodDiagnosed,
    required this.heartDisease,
    required this.kidneyDisease,
    required this.obesity,
    required this.none,
  });

  factory HealthProfileModel.fromJson(Map<String, dynamic> j) =>
      HealthProfileModel(
        id:           j['id'] as int,
        userId:       j['user_id'] as int,
        hypertension: j['hypertension'] as bool,
        bpStatus:     j['bp_status'] as String?,
        systolic:     j['systolic'] as int?,
        diastolic:    j['diastolic'] as int?,
        diabetes:     j['diabetes'] as bool,
        sugarStatus:  j['sugar_status'] as String?,
        fastingSugar: j['fasting_sugar'] != null ? (j['fasting_sugar'] as num).toDouble() : null,
        postMealSugar: j['post_meal_sugar'] != null ? (j['post_meal_sugar'] as num).toDouble() : null,
        thyroid:      j['thyroid'] as bool,
        thyroidType:  j['thyroid_type'] as String?,
        pcos:         j['pcos'] as bool,
        pcosDiagnosed: j['pcos_diagnosed'] as bool?,
        pcod:         j['pcod'] as bool,
        pcodDiagnosed: j['pcod_diagnosed'] as bool?,
        heartDisease: j['heart_disease'] as bool,
        kidneyDisease: j['kidney_disease'] as bool,
        obesity:      j['obesity'] as bool,
        none:         j['none'] as bool,
      );

  List<String> get activeConditions {
    final list = <String>[];
    if (hypertension) list.add('Hypertension (BP)');
    if (diabetes)     list.add('Diabetes');
    if (pcos)         list.add('PCOS');
    if (pcod)         list.add('PCOD');
    if (thyroid)      list.add('Thyroid');
    if (heartDisease) list.add('Heart Disease');
    if (kidneyDisease) list.add('Kidney Disease');
    if (obesity)      list.add('Obesity');
    if (none)         list.add('None');
    return list;
  }
}
