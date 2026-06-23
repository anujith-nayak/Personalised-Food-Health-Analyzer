"""BMI calculation utilities."""


def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    """BMI = weight(kg) / height(m)^2"""
    height_m = height_cm / 100
    return round(weight_kg / (height_m ** 2), 1)


def get_bmi_category(bmi: float) -> str:
    """Return BMI category label."""
    if bmi < 18.5:
        return "Underweight"
    elif bmi < 25.0:
        return "Normal Weight"
    elif bmi < 30.0:
        return "Overweight"
    else:
        return "Obese"
