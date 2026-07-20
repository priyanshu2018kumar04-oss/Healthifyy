from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, Date, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String(20), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    height_cm = Column(Float, nullable=False)
    activity_level = Column(String(20), default="moderate", nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    health_logs = relationship("HealthLog", back_populates="user", cascade="all, delete-orphan")
    goals = relationship("UserGoal", back_populates="user", cascade="all, delete-orphan")
    diet_plans = relationship("DietPlan", back_populates="user", cascade="all, delete-orphan")
    workout_plans = relationship("WorkoutPlan", back_populates="user", cascade="all, delete-orphan")
    weekly_progress = relationship("WeeklyProgress", back_populates="user", cascade="all, delete-orphan")


class HealthLog(Base):
    __tablename__ = "health_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Weight (always stored in kg)
    weight_kg = Column(Float, nullable=False)

    # Blood glucose (always stored in mmol/L)
    blood_glucose_mmol = Column(Float, nullable=False)

    # Blood pressure (optional)
    blood_pressure_sys = Column(Integer, nullable=True)   # Systolic
    blood_pressure_dia = Column(Integer, nullable=True)   # Diastolic

    # Cholesterol (optional, stored in mg/dL)
    cholesterol_mgdl = Column(Float, nullable=True)

    # After-meal glucose check (mmol/L, optional)
    after_meal_glucose = Column(Float, nullable=True)

    notes = Column(Text, nullable=True)
    logged_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationship
    user = relationship("User", back_populates="health_logs")


class UserGoal(Base):
    __tablename__ = "user_goals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    goal_type = Column(String(30), nullable=False)  # fat_loss, weight_gain, bodybuilding, maintain
    target_weight_kg = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="goals")


class DietPlan(Base):
    __tablename__ = "diet_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_date = Column(Date, default=datetime.utcnow().date, index=True)
    plan_json = Column(Text, nullable=False)   # Full AI-generated plan as JSON string
    total_calories = Column(Float, nullable=True)
    goal_type = Column(String(30), nullable=True)
    bmi_at_generation = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="diet_plans")


class WorkoutPlan(Base):
    __tablename__ = "workout_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_date = Column(Date, default=datetime.utcnow().date, index=True)
    plan_json = Column(Text, nullable=False)   # Full AI-generated plan as JSON string
    total_calories_burned = Column(Float, nullable=True)
    goal_type = Column(String(30), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="workout_plans")


class WeeklyProgress(Base):
    __tablename__ = "weekly_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    week_start = Column(Date, nullable=False)
    week_end = Column(Date, nullable=False)
    summary_json = Column(Text, nullable=False)   # AI-generated summary as JSON string
    health_score = Column(Float, nullable=True)
    generated_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="weekly_progress")
