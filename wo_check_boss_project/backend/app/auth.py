"""Lấy người dùng hiện tại.

Hệ thống giả định người dùng ĐÃ đăng nhập (SSO / nginx / middleware có sẵn).
File này chỉ đọc thông tin user đã được xác thực, không tự làm đăng nhập.
Nếu hệ thống của bạn đã có dependency kiểu `get_current_user`, thay hàm dưới đây bằng hàm đó.
"""
from dataclasses import dataclass, field
from urllib.parse import unquote

from fastapi import HTTPException, Request

from .config import DEV_USER

REVIEW_ROLES = {"reviewer", "admin"}


@dataclass
class User:
    username: str
    name: str
    roles: list = field(default_factory=list)

    @property
    def can_review(self) -> bool:
        return any(r in REVIEW_ROLES for r in self.roles)

    def to_dict(self):
        return {"username": self.username, "name": self.name, "roles": self.roles, "can_review": self.can_review}


def _roles(v) -> list:
    if not v:
        return []
    if isinstance(v, str):
        v = v.replace(";", ",").split(",")
    return [str(x).strip().lower() for x in v if str(x).strip()]


def get_current_user(request: Request) -> User:
    # 1) Middleware xác thực sẵn có đã gán request.state.user (object hoặc dict)
    u = getattr(request.state, "user", None)
    if u is not None:
        g = (lambda k: u.get(k)) if isinstance(u, dict) else (lambda k: getattr(u, k, None))
        username = g("username") or g("user_name") or g("employee_id") or g("id")
        if username:
            return User(str(username), g("full_name") or g("name") or str(username), _roles(g("roles") or g("role")))

    # 2) Reverse proxy / SSO gắn header (họ tên tiếng Việt nên URL-encode)
    h = request.headers
    username = h.get("X-Remote-User")
    if username:
        return User(username, unquote(h.get("X-Remote-Name") or username), _roles(h.get("X-Remote-Roles")))

    # 3) Chạy thử trên máy dev
    if DEV_USER:
        p = (DEV_USER.split("|") + ["", ""])[:3]
        return User(p[0], p[1] or p[0], _roles(p[2]))

    raise HTTPException(401, "Không xác định được người dùng đăng nhập")