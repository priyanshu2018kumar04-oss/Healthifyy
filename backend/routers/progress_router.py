"""Progress router — weekly reports, health trends, and manual report triggers."""
import json
from datetime import date, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from database import get_db
from models import User, HealthLog, UserGoal, WeeklyProgress
from schemas import WeeklyProgressResponse
from auth import get_current_user
from services.scheduler import generate_weekly_report_for_user

router = APIRouter()


@router.get("/weekly/latest", response_model=WeeklyProgressResponse)
def get_latest_weekly_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the most recent weekly progress report."""
    report = (
        db.query(WeeklyProgress)
        .filter(WeeklyProgress.user_id == current_user.id)
        .order_by(WeeklyProgress.generated_at.desc())
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="No weekly report available yet. Generate your first plan to start tracking.")
    return WeeklyProgressResponse(
        id=report.id,
        week_start=report.week_start,
        week_end=report.week_end,
        summary_json=json.loads(report.summary_json),
        health_score=report.health_score,
        generated_at=report.generated_at,
    )


@router.get("/weekly/history", response_model=List[WeeklyProgressResponse])
def get_weekly_history(
    limit: int = 8,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the last N weekly progress reports."""
    reports = (
        db.query(WeeklyProgress)
        .filter(WeeklyProgress.user_id == current_user.id)
        .order_by(WeeklyProgress.generated_at.desc())
        .limit(min(limit, 52))
        .all()
    )
    return [
        WeeklyProgressResponse(
            id=r.id,
            week_start=r.week_start,
            week_end=r.week_end,
            summary_json=json.loads(r.summary_json),
            health_score=r.health_score,
            generated_at=r.generated_at,
        )
        for r in reports
    ]


@router.post("/weekly/generate", status_code=202)
def trigger_weekly_report(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manually trigger weekly report generation (runs in background)."""
    background_tasks.add_task(generate_weekly_report_for_user, current_user.id)
    return {"message": "Weekly report generation started. You will receive an email and WhatsApp notification when ready.", "user_id": current_user.id}


@router.get("/health-trend")
def get_health_trend(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return time-series health data for charting (weight, glucose, cholesterol)."""
    logs = (
        db.query(HealthLog)
        .filter(HealthLog.user_id == current_user.id)
        .order_by(HealthLog.logged_at.asc())
        .limit(min(days, 90))
        .all()
    )
    return {
        "labels": [str(l.logged_at.date()) for l in logs],
        "weight_kg": [l.weight_kg for l in logs],
        "glucose_mmol": [l.blood_glucose_mmol for l in logs],
        "cholesterol": [l.cholesterol_mgdl for l in logs],
        "after_meal_glucose": [l.after_meal_glucose for l in logs],
    }


@router.get("/stats")
def get_user_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return aggregated health statistics for the dashboard."""
    from models import DietPlan, WorkoutPlan
    from services.health_calc import calculate_bmi, get_bmi_category

    total_logs  = db.query(HealthLog).filter(HealthLog.user_id == current_user.id).count()
    total_plans = db.query(DietPlan).filter(DietPlan.user_id == current_user.id).count()
    total_reports = db.query(WeeklyProgress).filter(WeeklyProgress.user_id == current_user.id).count()

    latest_log = (
        db.query(HealthLog)
        .filter(HealthLog.user_id == current_user.id)
        .order_by(HealthLog.logged_at.desc())
        .first()
    )

    latest_report = (
        db.query(WeeklyProgress)
        .filter(WeeklyProgress.user_id == current_user.id)
        .order_by(WeeklyProgress.generated_at.desc())
        .first()
    )

    bmi = None
    bmi_cat = None
    if latest_log:
        bmi = round(calculate_bmi(latest_log.weight_kg, current_user.height_cm), 1)
        bmi_cat = get_bmi_category(bmi)

    return {
        "total_health_logs": total_logs,
        "total_plans_generated": total_plans,
        "total_weekly_reports": total_reports,
        "latest_bmi": bmi,
        "bmi_category": bmi_cat,
        "latest_weight_kg": latest_log.weight_kg if latest_log else None,
        "latest_glucose_mmol": latest_log.blood_glucose_mmol if latest_log else None,
        "latest_health_score": json.loads(latest_report.summary_json).get("week_summary", {}).get("overall_health_score") if latest_report else None,
        "member_since": str(current_user.created_at.date()),
    }
