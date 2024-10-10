from typing import List, Optional

from datetime import date, time, datetime
from fastapi import Form
from pydantic import BaseModel, Field


class Workspace(BaseModel):
    title: str
    created_by: str
    users: Optional[List[str]] = [] 
    last_updated: Optional[datetime] = None

    @classmethod
    def from_form(
        cls,
        title: str = Form(...),
        created_by: str = Form(...),
        selected_users: str = Form("")
    ):
        return cls(
            title=title,
            created_by=created_by,
            users=[u.strip() for u in selected_users.split(",") if u.strip()] if selected_users else [],
            last_updated=datetime.utcnow()
        )


class Task(BaseModel):
    title: str
    details: Optional[str] = None
    workspace_id: str
    status: str = Field(..., description="One of: 'pending', 'in_progress', 'completed'")
    assigned_to: List[str] = []
    due_date: Optional[date] = None
    due_time: Optional[time] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    @classmethod
    def from_form(
        cls,
        title: str = Form(...),
        status: str = Form(...),
        assigned_to: str = Form(""),
        details: Optional[str] = Form(None),
        due_date: Optional[date] = Form(None),
        due_time: Optional[time] = Form(None),
    ):
        return cls(
            title=title,
            workspace_id="",
            status=status,
            details=details,
            assigned_to=[email.strip() for email in assigned_to.split(",") if email.strip()] if assigned_to else [],
            due_date=due_date,
            due_time=due_time,
            created_at=datetime.utcnow(),
        )
    

class User(BaseModel):
    id: str
    name: str
    email: str
    last_login: Optional[datetime] = None
    

class WorkspaceSummary(BaseModel):
    id: str
    title: str
    created_by: str
    total_mem: int
    users: List[str]
    total_tasks: int = 0
    active_tasks: int = 0
    completed_tasks: int = 0
    last_activity: Optional[datetime] = None


