"""Health data router — log, retrieve, and summarise health metrics."""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from database import get_db
from models import User, HealthLog, UserGoal
from schemas import HealthLogCreate, HealthLogResponse, UserGoalCreate, UserGoalResponse, HealthSummary
from auth import get_current_user
from services.health_calc import (
    convert_weight_to_kg,
    convert_glucose_to_mmol,
    calculate_bmi,
    get_bmi_category,
    get_recommended_goal,
    classify_glucose,
    classify_bp,
    classify_cholesterol,
    classify_after_meal_glucose,
)
from services.notifier import send_warning_alert

router = APIRouter()


def _build_warnings_from_log(log: HealthLog, height_cm: float) -> list:
    """Quick rule-based warnings for immediate notification after logging."""
    warnings = []
    bmi = calculate_bmi(log.weight_kg, height_cm)
    bmi_cat = get_bmi_category(bmi)

    if bmi < 16:
        warnings.append({
            "level": "critical", "category": "bmi",
            "title": "🔴 CRITICAL: Severely Underweight",
            "message": f"Your BMI is {round(bmi,1)} ({bmi_cat}).",
            "action": "Seek immediate medical attention.",
        })
    elif bmi >= 40:
        warnings.append({
            "level": "critical", "category": "bmi",
            "title": "🔴 CRITICAL: Severe Obesity",
            "message": f"Your BMI is {round(bmi,1)} ({bmi_cat}).",
            "action": "Consult a doctor immediately.",
        })
    elif bmi >= 30:
        warnings.append({
            "level": "high", "category": "bmi",
            "title": "⚠️ Obese — Action Required",
            "message": f"Your BMI is {round(bmi,1)} ({bmi_cat}).",
            "action": "Follow a calorie-deficit plan and increase activity.",
        })

    g_status = classify_glucose(log.blood_glucose_mmol)
    if g_status == "diabetic_range":
        warnings.append({
            "level": "critical", "category": "glucose",
            "title": "🔴 CRITICAL: Diabetic Range Blood Glucose",
            "message": f"Fasting glucose is {log.blood_glucose_mmol:.1f} mmol/L.",
            "action": "See a doctor immediately.",
        })
    elif g_status == "pre_diabetic":
        warnings.append({
            "level": "high", "category": "glucose",
            "title": "⚠️ Pre-Diabetic Blood Glucose",
            "message": f"Glucose is {log.blood_glucose_mmol:.1f} mmol/L.",
            "action": "Follow a low-GI diet and monitor weekly.",
        })

    if log.blood_pressure_sys and log.blood_pressure_dia:
        bp_status = classify_bp(log.blood_pressure_sys, log.blood_pressure_dia)
        if bp_status == "hypertension_stage2":
            warnings.append({
                "level": "critical", "category": "blood_pressure",
                "title": "🔴 CRITICAL: Hypertension Stage 2",
                "message": f"BP {log.blood_pressure_sys}/{log.blood_pressure_dia} mmHg.",
                "action": "Seek immediate medical attention.",
            })

    if log.cholesterol_mgdl and classify_cholesterol(log.cholesterol_mgdl) == "high":
        warnings.append({
            "level": "high", "category": "cholesterol",
            "title": "🔴 High Cholesterol",
            "message": f"Cholesterol {log.cholesterol_mgdl:.0f} mg/dL.",
            "action": "Follow a heart-healthy diet.",
        })

    if log.after_meal_glucose and classify_after_meal_glucose(log.after_meal_glucose) == "high":
        warnings.append({
            "level": "high", "category": "post_meal",
            "title": "🔴 High Post-Meal Blood Sugar Spike",
            "message": f"Post-meal glucose {log.after_meal_glucose:.1f} mmol/L.",
            "action": "Walk after meals and reduce high-GI foods.",
        })

    return warnings


def _notify_critical_warnings(user: User, warnings: list) -> None:
    for warning in warnings:
        if warning["level"] in ("critical", "high"):
            send_warning_alert(user.name, user.email, user.phone, warning)


# ─── Health Log Endpoints ──────────────────────────────────────────────────────

@router.post("/log", response_model=HealthLogResponse, status_code=status.HTTP_201_CREATED)
def log_health(
    body: HealthLogCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Log a new health data entry (weight, glucose, BP, cholesterol, after-meal glucose)."""
    # Convert inputs to canonical units
    weight_kg = convert_weight_to_kg(body.weight_value, body.weight_unit.value)
    glucose_mmol = convert_glucose_to_mmol(body.blood_glucose_value, body.glucose_unit.value)

    after_meal_mmol = None
    if body.after_meal_glucose_value:
        after_meal_mmol = convert_glucose_to_mmol(
            body.after_meal_glucose_value, body.after_meal_glucose_unit.value
        )

    log = HealthLog(
        user_id=current_user.id,
        weight_kg=round(weight_kg, 2),
        blood_glucose_mmol=round(glucose_mmol, 2),
        blood_pressure_sys=body.blood_pressure_sys,
        blood_pressure_dia=body.blood_pressure_dia,
        cholesterol_mgdl=body.cholesterol_mgdl,
        after_meal_glucose=round(after_meal_mmol, 2) if after_meal_mmol else None,
        notes=body.notes,
        logged_at=datetime.utcnow(),
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    warnings = _build_warnings_from_log(log, current_user.height_cm)
    if warnings:
        background_tasks.add_task(_notify_critical_warnings, current_user, warnings)

    return log


@router.get("/latest", response_model=HealthLogResponse)
def get_latest_log(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve the most recent health log entry."""
    log = (
        db.query(HealthLog)
        .filter(HealthLog.user_id == current_user.id)
        .order_by(HealthLog.logged_at.desc())
        .first()
    )
    if not log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No health data found. Please log your first entry.")
    return log


@router.get("/history", response_model=List[HealthLogResponse])
def get_history(
    limit: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve the last N health log entries."""
    return (
        db.query(HealthLog)
        .filter(HealthLog.user_id == current_user.id)
        .order_by(HealthLog.logged_at.desc())
        .limit(min(limit, 90))
        .all()
    )


@router.get("/summary", response_model=HealthSummary)
def get_health_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return a computed health summary from the latest log entry."""
    log = (
        db.query(HealthLog)
        .filter(HealthLog.user_id == current_user.id)
        .order_by(HealthLog.logged_at.desc())
        .first()
    )
    if not log:
        raise HTTPException(status_code=404, detail="No health data found.")

    bmi = calculate_bmi(log.weight_kg, current_user.height_cm)
    bmi_cat = get_bmi_category(bmi)
    rec_goal = get_recommended_goal(bmi)

    bp_str = None
    if log.blood_pressure_sys and log.blood_pressure_dia:
        bp_str = f"{log.blood_pressure_sys}/{log.blood_pressure_dia} mmHg"

    return HealthSummary(
        bmi=round(bmi, 1),
        bmi_category=bmi_cat,
        weight_kg=log.weight_kg,
        blood_glucose_mmol=log.blood_glucose_mmol,
        blood_pressure=bp_str,
        cholesterol_mgdl=log.cholesterol_mgdl,
        recommended_goal=rec_goal,
        logged_at=log.logged_at,
    )


# ─── Goal Endpoints ────────────────────────────────────────────────────────────

@router.post("/goal", response_model=UserGoalResponse, status_code=status.HTTP_201_CREATED)
def set_goal(
    body: UserGoalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Set or update the user's current health goal."""
    # Deactivate any previous goals
    db.query(UserGoal).filter(
        UserGoal.user_id == current_user.id, UserGoal.is_active == True
    ).update({"is_active": False})

    goal = UserGoal(
        user_id=current_user.id,
        goal_type=body.goal_type.value,
        target_weight_kg=body.target_weight_kg,
        is_active=True,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


@router.get("/goal", response_model=UserGoalResponse)
def get_goal(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the user's active health goal."""
    goal = (
        db.query(UserGoal)
        .filter(UserGoal.user_id == current_user.id, UserGoal.is_active == True)
        .order_by(UserGoal.created_at.desc())
        .first()
    )
    if not goal:
        raise HTTPException(status_code=404, detail="No active goal set. Please set your goal first.")
    return goal
