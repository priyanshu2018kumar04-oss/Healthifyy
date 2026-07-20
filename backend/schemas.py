from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List, Any, Dict
from datetime import datetime, date
from enum import Enum


# ─── Enums ────────────────────────────────────────────────────────────────────

class Gender(str, Enum):
    male = "male"
    female = "female"
    other = "other"

class GoalType(str, Enum):
    fat_loss = "fat_loss"
    weight_gain = "weight_gain"
    bodybuilding = "bodybuilding"
    maintain = "maintain"

class ActivityLevel(str, Enum):
    sedentary = "sedentary"
    light = "light"
    moderate = "moderate"
    active = "active"
    very_active = "very_active"

class WeightUnit(str, Enum):
    kg = "kg"
    lbs = "lbs"
    stone = "stone"

class GlucoseUnit(str, Enum):
    mmol_L = "mmol/L"
    mg_dL = "mg/dL"


# ─── Auth Schemas ──────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Full name")
    age: int = Field(..., ge=10, le=120, description="Age in years")
    gender: Gender
    email: EmailStr
    password: str = Field(..., min_length=6, description="Minimum 6 characters")
    phone: Optional[str] = Field(None, description="WhatsApp-enabled phone number with country code e.g. +919876543210")
    height_cm: float = Field(..., ge=100, le=250, description="Height in centimeters")
    activity_level: ActivityLevel = ActivityLevel.moderate

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Optional[Dict[str, Any]] = None

class UserResponse(BaseModel):
    id: int
    name: str
    age: int
    gender: str
    email: str
    phone: Optional[str]
    height_cm: float
    activity_level: str
    created_at: datetime

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    phone: Optional[str] = None
    height_cm: Optional[float] = None
    activity_level: Optional[ActivityLevel] = None


# ─── Health Log Schemas ────────────────────────────────────────────────────────

class HealthLogCreate(BaseModel):
    weight_value: float = Field(..., gt=0, description="Body weight")
    weight_unit: WeightUnit = WeightUnit.kg
    blood_glucose_value: float = Field(..., gt=0, description="Fasting blood glucose")
    glucose_unit: GlucoseUnit = GlucoseUnit.mmol_L
    blood_pressure_sys: Optional[int] = Field(None, ge=60, le=250, description="Systolic BP (optional)")
    blood_pressure_dia: Optional[int] = Field(None, ge=40, le=150, description="Diastolic BP (optional)")
    cholesterol_mgdl: Optional[float] = Field(None, ge=0, description="Cholesterol in mg/dL (optional)")
    after_meal_glucose_value: Optional[float] = Field(None, gt=0, description="Post-meal glucose (optional)")
    after_meal_glucose_unit: GlucoseUnit = GlucoseUnit.mmol_L
    notes: Optional[str] = Field(None, max_length=500)

class HealthLogResponse(BaseModel):
    id: int
    user_id: int
    weight_kg: float
    blood_glucose_mmol: float
    blood_pressure_sys: Optional[int]
    blood_pressure_dia: Optional[int]
    cholesterol_mgdl: Optional[float]
    after_meal_glucose: Optional[float]
    notes: Optional[str]
    logged_at: datetime

    class Config:
        from_attributes = True

class HealthSummary(BaseModel):
    bmi: float
    bmi_category: str
    weight_kg: float
    blood_glucose_mmol: float
    blood_pressure: Optional[str]
    cholesterol_mgdl: Optional[float]
    recommended_goal: str
    logged_at: datetime


# ─── Goal Schemas ──────────────────────────────────────────────────────────────

class UserGoalCreate(BaseModel):
    goal_type: GoalType
    target_weight_kg: Optional[float] = Field(None, gt=0)

class UserGoalResponse(BaseModel):
    id: int
    user_id: int
    goal_type: str
    target_weight_kg: Optional[float]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Plan Schemas ──────────────────────────────────────────────────────────────

class PlanGenerateRequest(BaseModel):
    include_yoga: bool = True
    generate_weekly: bool = False

class PlanResponse(BaseModel):
    success: bool
    diet_plan: Optional[Dict[str, Any]] = None
    workout_plan: Optional[Dict[str, Any]] = None
    warnings: List[Dict[str, Any]] = []
    bmi: Optional[float] = None
    bmi_category: Optional[str] = None
    calorie_target: Optional[float] = None
    bmr: Optional[float] = None
    tdee: Optional[float] = None
    weekly_summary: Optional[Dict[str, Any]] = None
    notifications_sent: Optional[Dict[str, bool]] = None
    error: Optional[str] = None

class DietPlanResponse(BaseModel):
    id: int
    plan_date: date
    plan_json: Dict[str, Any]
    total_calories: Optional[float]
    goal_type: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class WorkoutPlanResponse(BaseModel):
    id: int
    plan_date: date
    plan_json: Dict[str, Any]
    total_calories_burned: Optional[float]
    goal_type: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Progress Schemas ──────────────────────────────────────────────────────────

class WeeklyProgressResponse(BaseModel):
    id: int
    week_start: date
    week_end: date
    summary_json: Dict[str, Any]
    health_score: Optional[float]
    generated_at: datetime

    class Config:
        from_attributes = True

class ProgressHistoryItem(BaseModel):
    date: str
    weight_kg: float
    blood_glucose_mmol: float
    cholesterol_mgdl: Optional[float]
    blood_pressure: Optional[str]

class NotifyTestRequest(BaseModel):
    type: str = "daily"  # "daily" or "weekly"
