class UserModel {
  final int id;
  final String name;
  final String email;
  final int age;
  final String gender;
  final double height;
  final double weight;
  final String foodPreference;
  final double? bmiScore;
  final String? bmiCategory;

  const UserModel({
    required this.id,
    required this.name,
    required this.email,
    required this.age,
    required this.gender,
    required this.height,
    required this.weight,
    required this.foodPreference,
    this.bmiScore,
    this.bmiCategory,
  });

  factory UserModel.fromJson(Map<String, dynamic> j) => UserModel(
        id:             j['id'] as int,
        name:           j['name'] as String,
        email:          j['email'] as String,
        age:            j['age'] as int,
        gender:         j['gender'] as String,
        height:         (j['height'] as num).toDouble(),
        weight:         (j['weight'] as num).toDouble(),
        foodPreference: j['food_preference'] as String,
        bmiScore:       j['bmi_score'] != null ? (j['bmi_score'] as num).toDouble() : null,
        bmiCategory:    j['bmi_category'] as String?,
      );
}
