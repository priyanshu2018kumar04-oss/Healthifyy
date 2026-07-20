"""Plan router — trigger AI plan generation and retrieve saved plans."""
import json
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import User, HealthLog, UserGoal, DietPlan, WorkoutPlan
from schemas import PlanGenerateRequest, PlanResponse, DietPlanResponse, WorkoutPlanResponse
from auth import get_current_user
from agent.graph import health_graph
from services.notifier import send_daily_notifications

router = APIRouter()


def _build_initial_state(user: User, log: HealthLog, goal: UserGoal, opts: PlanGenerateRequest, historical: list) -> dict:
    return {
        "user_id": user.id,
        "user_profile": {
            "name": user.name,
            "age": user.age,
            "gender": user.gender,
            "height_cm": user.height_cm,
            "goal": goal.goal_type if goal else "maintain",
            "activity_level": user.activity_level,
        },
        "health_metrics": {
            "weight_kg": log.weight_kg,
            "blood_glucose_mmol": log.blood_glucose_mmol,
            "blood_pressure_sys": log.blood_pressure_sys,
            "blood_pressure_dia": log.blood_pressure_dia,
            "cholesterol_mgdl": log.cholesterol_mgdl,
            "after_meal_glucose": log.after_meal_glucose,
        },
        "historical_data": historical,
        "include_yoga": opts.include_yoga,
        "generate_weekly": opts.generate_weekly,
        # Placeholders filled by agent nodes
        "bmi": 0.0, "bmi_category": "", "bmr": 0.0,
        "tdee": 0.0, "calorie_target": 0.0,
        "health_analysis": {}, "warnings": [],
        "diet_plan": {}, "workout_plan": {}, "weekly_summary": {},
        "notifications_sent": False, "errors": [],
    }


@router.post("/generate", response_model=PlanResponse)
def generate_plan(
    body: PlanGenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Run the full LangGraph AI pipeline and return personalised
    diet + workout plans, health warnings, and computed metrics.
    Plans are persisted to the database.
    """
    # Require a health log
    log = (
        db.query(HealthLog)
        .filter(HealthLog.user_id == current_user.id)
        .order_by(HealthLog.logged_at.desc())
        .first()
    )
    if not log:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No health data found. Please log your health metrics first.",
        )

    # Get active goal (optional — default to maintain)
    goal = (
        db.query(UserGoal)
        .filter(UserGoal.user_id == current_user.id, UserGoal.is_active == True)
        .order_by(UserGoal.created_at.desc())
        .first()
    )

    # Last 7 health logs for weekly context / trend analysis
    recent_logs = (
        db.query(HealthLog)
        .filter(HealthLog.user_id == current_user.id)
        .order_by(HealthLog.logged_at.desc())
        .limit(7)
        .all()
    )
    historical = [
        {
            "date": str(entry.logged_at.date()),
            "weight_kg": entry.weight_kg,
            "blood_glucose_mmol": entry.blood_glucose_mmol,
            "cholesterol_mgdl": entry.cholesterol_mgdl,
        }
        for entry in recent_logs
    ]

    # Build initial state and run the graph
    try:
        initial_state = _build_initial_state(current_user, log, goal, body, historical)
        result = health_graph.invoke(initial_state)
    except ValueError as e:
        # Likely a missing API key
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI plan generation failed: {str(e)}",
        )

    diet_plan    = result.get("diet_plan", {})
    workout_plan = result.get("workout_plan", {})

    # Persist diet plan
    dp = DietPlan(
        user_id=current_user.id,
        plan_date=date.today(),
        plan_json=json.dumps(diet_plan),
        total_calories=diet_plan.get("calorie_target"),
        goal_type=goal.goal_type if goal else "maintain",
        bmi_at_generation=result.get("bmi"),
    )
    db.add(dp)

    # Persist workout plan
    wp = WorkoutPlan(
        user_id=current_user.id,
        plan_date=date.today(),
        plan_json=json.dumps(workout_plan),
        total_calories_burned=workout_plan.get("total_calories_burned"),
        goal_type=goal.goal_type if goal else "maintain",
    )
    db.add(wp)
    db.commit()

    # Send notifications in background (non-blocking)
    background_tasks.add_task(
        send_daily_notifications,
        user_name=current_user.name,
        user_email=current_user.email,
        user_phone=current_user.phone,
        warnings=result.get("warnings", []),
        diet_plan=diet_plan,
        workout_plan=workout_plan,
    )

    return PlanResponse(
        success=True,
        diet_plan=diet_plan,
        workout_plan=workout_plan,
        warnings=result.get("warnings", []),
        bmi=result.get("bmi"),
        bmi_category=result.get("bmi_category"),
        calorie_target=result.get("calorie_target"),
        bmr=result.get("bmr"),
        tdee=result.get("tdee"),
        weekly_summary=result.get("weekly_summary") or None,
        notifications_sent={"scheduled": True},
    )


@router.get("/diet/latest", response_model=DietPlanResponse)
def get_latest_diet(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the most recently generated diet plan."""
    plan = (
        db.query(DietPlan)
        .filter(DietPlan.user_id == current_user.id)
        .order_by(DietPlan.created_at.desc())
        .first()
    )
    if not plan:
        raise HTTPException(status_code=404, detail="No diet plan found. Please generate a plan first.")
    return DietPlanResponse(
        id=plan.id,
        plan_date=plan.plan_date,
        plan_json=json.loads(plan.plan_json),
        total_calories=plan.total_calories,
        goal_type=plan.goal_type,
        created_at=plan.created_at,
    )


@router.get("/diet/history", response_model=List[DietPlanResponse])
def get_diet_history(
    limit: int = 7,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the last N diet plans."""
    plans = (
        db.query(DietPlan)
        .filter(DietPlan.user_id == current_user.id)
        .order_by(DietPlan.created_at.desc())
        .limit(min(limit, 30))
        .all()
    )
    return [
        DietPlanResponse(
            id=p.id, plan_date=p.plan_date,
            plan_json=json.loads(p.plan_json),
            total_calories=p.total_calories,
            goal_type=p.goal_type, created_at=p.created_at,
        )
        for p in plans
    ]


@router.get("/workout/latest", response_model=WorkoutPlanResponse)
def get_latest_workout(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the most recently generated workout plan."""
    plan = (
        db.query(WorkoutPlan)
        .filter(WorkoutPlan.user_id == current_user.id)
        .order_by(WorkoutPlan.created_at.desc())
        .first()
    )
    if not plan:
        raise HTTPException(status_code=404, detail="No workout plan found. Please generate a plan first.")
    return WorkoutPlanResponse(
        id=plan.id,
        plan_date=plan.plan_date,
        plan_json=json.loads(plan.plan_json),
        total_calories_burned=plan.total_calories_burned,
        goal_type=plan.goal_type,
        created_at=plan.created_at,
    )
