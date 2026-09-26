from fastapi import Request, HTTPException, status, Depends
from typing import Optional, List
from src.db import get_db

class AuthUser:
    def __init__(self, id: str, name: str, email: str, role: str, session_token: str):
        self.id = id
        self.name = name
        self.email = email
        self.role = role
        self.session_token = session_token

    def is_judge(self) -> bool:
        return self.role in ("judge", "admin")

    def is_organizer(self) -> bool:
        return self.role in ("organizer", "admin")

    def is_participant(self) -> bool:
        return self.role in ("participant", "admin")

def extract_token_from_request(request: Request) -> Optional[str]:
    # 1. Check Cookie header: session=<token>
    cookies = request.cookies
    if "session" in cookies and cookies["session"]:
        return cookies["session"]
    
    raw_cookie = request.headers.get("cookie")
    if raw_cookie:
        for part in raw_cookie.split(";"):
            if "=" in part:
                k, v = part.strip().split("=", 1)
                if k.strip() == "session":
                    return v.strip()

    # 2. Check Authorization header: Bearer <token>
    auth_header = request.headers.get("authorization")
    if auth_header:
        parts = auth_header.strip().split(" ")
        if len(parts) == 2 and parts[0].lower() in ("bearer", "token", "session"):
            return parts[1]
        elif len(parts) == 1:
            return parts[0]

    return None

def get_current_user_optional(request: Request) -> Optional[AuthUser]:
    token = extract_token_from_request(request)
    if not token:
        return None

    with get_db() as conn:
        row = conn.execute(
            "SELECT id, name, email, role, session_token FROM users WHERE session_token = ?", 
            (token,)
        ).fetchone()
        if row:
            return AuthUser(
                id=row["id"],
                name=row["name"],
                email=row["email"],
                role=row["role"],
                session_token=row["session_token"]
            )
    return None

def get_current_user(request: Request) -> AuthUser:
    user = get_current_user_optional(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid session."
        )
    return user

def require_role(allowed_roles: List[str]):
    def role_checker(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if user.role not in allowed_roles and user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: role '{user.role}' is not authorized."
            )
        return user
    return role_checker

require_organizer = require_role(["organizer", "admin"])
require_judge = require_role(["judge", "admin"])
require_participant = require_role(["participant", "admin"])
