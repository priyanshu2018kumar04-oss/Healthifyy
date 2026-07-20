"""LangGraph Agent State definition."""
from typing import TypedDict, List


class Warning(TypedDict):
    level: str       # info | moderate | high | critical
    category: str    # bmi | glucose | blood_pressure | cholesterol | post_meal
    title: str
    message: str
    action: str


class AgentState(TypedDict):
    # User context
    user_id: int
    user_profile: dict          # name, age, gender, height_cm, goal, activity_level
    health_metrics: dict        # weight_kg, blood_glucose_mmol, blood_pressure_sys,
                                # blood_pressure_dia, cholesterol_mgdl, after_meal_glucose
    historical_data: List[dict] # Last 7 days of health logs for weekly report
    include_yoga: bool

    # Computed health values
    bmi: float
    bmi_category: str
    bmr: float
    tdee: float
    calorie_target: float
    health_analysis: dict       # Classified risk levels for each metric

    # Agent outputs
    warnings: List[Warning]
    diet_plan: dict
    workout_plan: dict
    weekly_summary: dict

    # Control flags
    generate_weekly: bool
    notifications_sent: bool
    errors: List[str]
