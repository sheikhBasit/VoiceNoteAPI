import uuid
import time
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session

from app.db import models
from app.db.session import get_db
from app.services.auth_service import get_current_user
from app.utils.json_logger import JLogger
from app.core.limiter import limiter

router = APIRouter(prefix="/api/v1/teams", tags=["Teams"])

@router.post("", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def create_team(
    request: Request,
    name: str = Query(..., min_length=1, max_length=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Create a new team owned by the current user."""
    team_id = str(uuid.uuid4())
    new_team = models.Team(
        id=team_id,
        name=name,
        owner_id=current_user.id,
        created_at=int(time.time() * 1000)
    )
    # Owner is automatically a member
    new_team.members.append(current_user)
    
    try:
        db.add(new_team)
        db.commit()
        db.refresh(new_team)
        JLogger.info("Team created", team_id=team_id, owner_id=current_user.id)
    except Exception as e:
        db.rollback()
        JLogger.error("Failed to create team", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create team")
    
    return {
        "id": new_team.id,
        "name": new_team.name,
        "owner_id": new_team.owner_id,
        "member_count": len(new_team.members)
    }

@router.get("", response_model=List[dict])
def list_my_teams(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """List teams the user owns or is a member of."""
    # Combine owned and joined teams
    teams = current_user.owned_teams + current_user.teams
    # Remove duplicates if any (though logic should prevent it)
    unique_teams = {t.id: t for t in teams}.values()
    
    return [
        {
            "id": t.id,
            "name": t.name,
            "owner_id": t.owner_id,
            "is_owner": t.owner_id == current_user.id
        }
        for t in unique_teams
    ]

@router.post("/{team_id}/members", status_code=status.HTTP_200_OK)
def add_team_member(
    team_id: str,
    user_email: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Add a member to the team by email. Only owner can add members."""
    team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    if team.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the team owner can add members")
    
    new_member = db.query(models.User).filter(models.User.email == user_email).first()
    if not new_member:
        raise HTTPException(status_code=404, detail="User not found with this email")
    
    if new_member in team.members:
        return {"message": "User is already a member of this team"}
    
    team.members.append(new_member)
    db.commit()
    
    JLogger.info("Member added to team", team_id=team_id, user_id=new_member.id)
    return {"message": f"User {user_email} added to team {team.name}"}

@router.delete("/{team_id}/members/{user_id}", status_code=status.HTTP_200_OK)
def remove_team_member(
    team_id: str,
    user_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Remove a member from the team. Only owner can remove members."""
    team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    if team.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the team owner can remove members")
    
    if user_id == team.owner_id:
        raise HTTPException(status_code=400, detail="Owner cannot be removed from team")
    
    member_to_remove = db.query(models.User).filter(models.User.id == user_id).first()
    if not member_to_remove or member_to_remove not in team.members:
        raise HTTPException(status_code=404, detail="Member not found in team")
    
    team.members.remove(member_to_remove)
    db.commit()
    
    return {"message": "Member removed successfully"}


@router.get("/{team_id}/analytics")
def get_team_analytics(
    team_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    GET /analytics: Team-level metrics and AI-generated progress narratives.
    Only team members can access this.
    """
    team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Check if user is a member
    if current_user not in team.members and team.owner_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to view team analytics"
        )

    from app.services.analytics_service import AnalyticsService

    return AnalyticsService.get_full_team_analytics(db, team_id)
