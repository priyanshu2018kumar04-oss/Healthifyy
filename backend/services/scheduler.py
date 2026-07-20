"""
APScheduler-based background scheduler for weekly health reports.
The scheduler fires every Sunday at 8 AM and generates weekly progress
reports + sends email/WhatsApp notifications to all active users.
"""

import json
import logging
from datetime import date, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from database import SessionLocal
from models import User, HealthLog, DietPlan, WorkoutPlan, WeeklyProgress
from agent.graph import health_graph
from services.notifier import send_weekly_notifications

logger = logging.getLogger("healthify.scheduler")


def generate_weekly_report_for_user(user_id: int) -> bool:
    """Generate and save a weekly report for a single user."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user:
            return False

        # Fetch latest health log
        latest_log = (
            db.query(HealthLog)
            .filter(HealthLog.user_id == user_id)
            .order_by(HealthLog.logged_at.desc())
            .first()
        )
        if not latest_log:
            logger.info(f"No health data for user {user_id} — skipping weekly report")
            return False

        # Fetch last 7 health logs for historical data
        week_logs = (
            db.query(HealthLog)
            .filter(HealthLog.user_id == user_id)
            .order_by(HealthLog.logged_at.desc())
            .limit(7)
            .all()
        )

        # Get active goal
        from models import UserGoal
        goal = (
            db.query(UserGoal)
            .filter(UserGoal.user_id == user_id, UserGoal.is_active == True)
            .order_by(UserGoal.created_at.desc())
            .first()
        )

        historical = [
            {
                "date": str(log.logged_at.date()),
                "weight_kg": log.weight_kg,
                "blood_glucose_mmol": log.blood_glucose_mmol,
                "cholesterol_mgdl": log.cholesterol_mgdl,
            }
            for log in week_logs
        ]

        initial_state = {
            "user_id": user_id,
            "user_profile": {
                "name": user.name,
                "age": user.age,
                "gender": user.gender,
                "height_cm": user.height_cm,
                "goal": goal.goal_type if goal else "maintain",
                "activity_level": user.activity_level,
            },
            "health_metrics": {
                "weight_kg": latest_log.weight_kg,
                "blood_glucose_mmol": latest_log.blood_glucose_mmol,
                "blood_pressure_sys": latest_log.blood_pressure_sys,
                "blood_pressure_dia": latest_log.blood_pressure_dia,
                "cholesterol_mgdl": latest_log.cholesterol_mgdl,
                "after_meal_glucose": latest_log.after_meal_glucose,
            },
            "historical_data": historical,
            "include_yoga": True,
            "generate_weekly": True,
            "bmi": 0.0, "bmi_category": "", "bmr": 0.0,
            "tdee": 0.0, "calorie_target": 0.0,
            "health_analysis": {}, "warnings": [],
            "diet_plan": {}, "workout_plan": {}, "weekly_summary": {},
            "notifications_sent": False, "errors": [],
        }

        result = health_graph.invoke(initial_state)

        # Save weekly progress to DB
        today = date.today()
        week_start = today - timedelta(days=today.weekday() + 1)  # Last Sunday
        week_end = today

        progress = WeeklyProgress(
            user_id=user_id,
            week_start=week_start,
            week_end=week_end,
            summary_json=json.dumps(result.get("weekly_summary", {})),
            health_score=result.get("weekly_summary", {})
                              .get("week_summary", {})
                              .get("overall_health_score"),
        )
        db.add(progress)
        db.commit()

        # Send notifications
        send_weekly_notifications(
            user_name=user.name,
            user_email=user.email,
            user_phone=user.phone,
            weekly_summary=result.get("weekly_summary", {}),
            warnings=result.get("warnings", []),
        )

        logger.info(f"Weekly report generated and sent for user {user_id}")
        return True

    except Exception as e:
        logger.error(f"Weekly report error for user {user_id}: {e}")
        return False
    finally:
        db.close()


def run_weekly_reports():
    """Scheduled job: generate weekly reports for all active users."""
    logger.info("Starting scheduled weekly health report generation...")
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.is_active == True).all()
        user_ids = [u.id for u in users]
    finally:
        db.close()

    success_count = 0
    for uid in user_ids:
        if generate_weekly_report_for_user(uid):
            success_count += 1

    logger.info(f"Weekly reports completed: {success_count}/{len(user_ids)} users")


def create_scheduler() -> BackgroundScheduler:
    """Create and return a configured APScheduler instance."""
    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")

    # Every Sunday at 8:00 AM IST
    scheduler.add_job(
        run_weekly_reports,
        CronTrigger(day_of_week="sun", hour=8, minute=0),
        id="weekly_health_reports",
        name="Weekly Health Progress Reports",
        replace_existing=True,
        misfire_grace_time=3600,  # Allow up to 1 hour late
    )

    return scheduler
