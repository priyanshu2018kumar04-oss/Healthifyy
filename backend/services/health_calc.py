"""Health calculation utilities — BMI, BMR, TDEE, unit conversions."""


# ─── BMI ───────────────────────────────────────────────────────────────────────

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
    else:
        return "Severely Obese (Class III)"


def get_bmi_severity(bmi: float) -> str:
    """Return severity level for warning system."""
    if bmi < 16 or bmi >= 40:
        return "critical"
    elif bmi < 18.5 or bmi >= 35:
        return "high"
    elif bmi >= 30:
        return "high"
    elif bmi >= 25:
        return "moderate"
    return "normal"


# ─── BMR & TDEE ───────────────────────────────────────────────────────────────

def calculate_bmr(weight_kg: float, height_cm: float, age: int, gender: str) -> float:
    """Mifflin-St Jeor Equation (most accurate for most adults)."""
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    if gender.lower() in ("male", "m"):
        return base + 5
    else:
        return base - 161


def calculate_tdee(bmr: float, activity_level: str = "moderate") -> float:
    """Total Daily Energy Expenditure based on activity multiplier."""
    activity_factors = {
        "sedentary": 1.2,       # Desk job, no exercise
        "light": 1.375,         # Light exercise 1-3 days/week
        "moderate": 1.55,       # Moderate exercise 3-5 days/week
        "active": 1.725,        # Hard exercise 6-7 days/week
        "very_active": 1.9,     # Physical job + hard training
    }
    return bmr * activity_factors.get(activity_level, 1.55)


def get_calorie_target(tdee: float, goal: str) -> float:
    """Adjust TDEE based on user's goal."""
    adjustments = {
        "fat_loss": -500,       # ~0.5 kg/week loss
        "weight_gain": 400,     # ~0.4 kg/week lean gain
        "bodybuilding": 250,    # Lean bulk
        "maintain": 0,
    }
    target = tdee + adjustments.get(goal, 0)
    return max(target, 1200)    # Never go below 1200 kcal


def get_recommended_goal(bmi: float) -> str:
    """AI-recommended goal based on BMI."""
    if bmi < 18.5:
        return "weight_gain"
    elif bmi < 25:
        return "maintain"
    else:
        return "fat_loss"


def get_macro_targets(calorie_target: float, goal: str) -> dict:
    """Calculate macro targets (g) based on goal."""
    macro_ratios = {
        "fat_loss":    {"protein": 0.40, "carbs": 0.30, "fat": 0.30},
        "weight_gain": {"protein": 0.25, "carbs": 0.50, "fat": 0.25},
        "bodybuilding":{"protein": 0.35, "carbs": 0.45, "fat": 0.20},
        "maintain":    {"protein": 0.25, "carbs": 0.50, "fat": 0.25},
    }
    ratios = macro_ratios.get(goal, macro_ratios["maintain"])
    return {
        "protein_g": round(calorie_target * ratios["protein"] / 4),  # 4 kcal/g
        "carbs_g":   round(calorie_target * ratios["carbs"] / 4),
        "fat_g":     round(calorie_target * ratios["fat"] / 9),      # 9 kcal/g
    }


# ─── Unit Conversions ─────────────────────────────────────────────────────────

def convert_weight_to_kg(value: float, unit: str) -> float:
    conversions = {
        "kg": 1.0,
        "lbs": 0.453592,
        "stone": 6.35029,
    }
    return value * conversions.get(unit, 1.0)


def convert_glucose_to_mmol(value: float, unit: str) -> float:
    if unit == "mg/dL":
        return value / 18.0182
    return value  # already mmol/L


def convert_glucose_to_mgdl(mmol: float) -> float:
    return mmol * 18.0182


# ─── Health Risk Thresholds ───────────────────────────────────────────────────

GLUCOSE_THRESHOLDS = {
    "normal": (0, 5.6),
    "pre_diabetic": (5.6, 7.0),
    "diabetic": (7.0, float("inf")),
}

AFTER_MEAL_THRESHOLDS = {
    "normal": (0, 7.8),
    "elevated": (7.8, 11.1),
    "high": (11.1, float("inf")),
}

BP_THRESHOLDS = {
    "normal":     (0, 120, 0, 80),
    "elevated":   (120, 130, 80, 90),
    "hypertension1": (130, 140, 80, 90),
    "hypertension2": (140, float("inf"), 90, float("inf")),
}

CHOLESTEROL_THRESHOLDS = {
    "normal":     (0, 200),
    "borderline": (200, 240),
    "high":       (240, float("inf")),
}


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
