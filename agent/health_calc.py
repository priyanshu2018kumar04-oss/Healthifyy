"""Health calculation utilities used by the LangGraph agent nodes."""


def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    if height_cm <= 0:
        return 0.0
    height_m = height_cm / 100.0
    return weight_kg / (height_m ** 2)


def get_bmi_category(bmi: float) -> str:
    if bmi < 16:
        return "Severely Underweight"
    elif bmi < 18.5:
        return "Underweight"
    elif bmi < 25:
        return "Normal Weight"
    elif bmi < 30:
        return "Overweight"
    elif bmi < 35:
        return "Obese (Class I)"
    elif bmi < 40:
        return "Obese (Class II)"
    return "Severely Obese (Class III)"


def get_bmi_severity(bmi: float) -> str:
    if bmi < 16 or bmi >= 40:
        return "critical"
    elif bmi < 18.5 or bmi >= 35:
        return "high"
    elif bmi >= 30:
        return "high"
    elif bmi >= 25:
        return "moderate"
    return "normal"


def calculate_bmr(weight_kg: float, height_cm: float, age: int, gender: str) -> float:
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    if gender.lower() in ("male", "m"):
        return base + 5
    return base - 161


def calculate_tdee(bmr: float, activity_level: str = "moderate") -> float:
    activity_factors = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very_active": 1.9,
    }
    return bmr * activity_factors.get(activity_level, 1.55)


def get_calorie_target(tdee: float, goal: str) -> float:
    adjustments = {
        "fat_loss": -500,
        "weight_gain": 400,
        "bodybuilding": 250,
        "maintain": 0,
    }
    return max(tdee + adjustments.get(goal, 0), 1200)


def classify_glucose(mmol: float) -> str:
    if mmol >= 7.0:
        return "diabetic_range"
    elif mmol >= 5.6:
        return "pre_diabetic"
    return "normal"


def classify_bp(sys: int, dia: int) -> str:
    if sys >= 140 or dia >= 90:
        return "hypertension_stage2"
    elif sys >= 130 or dia >= 80:
        return "hypertension_stage1"
    elif sys >= 120:
        return "elevated"
    return "normal"


def classify_cholesterol(mgdl: float) -> str:
    if mgdl >= 240:
        return "high"
    elif mgdl >= 200:
        return "borderline"
    return "normal"


def classify_after_meal_glucose(mmol: float) -> str:
    if mmol >= 11.1:
        return "high"
    elif mmol >= 7.8:
        return "elevated"
    return "normal"
