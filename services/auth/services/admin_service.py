"""Platform admin service — account management, user management, metrics, impersonation."""

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from flask_jwt_extended import create_access_token, create_refresh_token
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from services.auth.models.admin_audit_log import AdminAuditLog, log_admin_audit
from services.auth.models.models import Account, PlanTier, User
from services.shared.logging import get_logger

logger = get_logger("admin_service")


class AdminServiceError(Exception):
    """Base exception for admin service errors."""

    def __init__(self, message: str, code: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class AdminService:
    """Platform admin operations — cross-account management."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Accounts ────────────────────────────────────────────────────

    def list_accounts(
        self,
        *,
        page: int = 1,
        per_page: int = 25,
        search: str | None = None,
        plan_tier: str | None = None,
        is_suspended: bool | None = None,
    ) -> dict[str, Any]:
        """List all accounts with pagination and filters."""
        query = select(Account).where(Account.deleted_at.is_(None))

        if search:
            query = query.where(Account.name.ilike(f"%{search}%"))
        if plan_tier:
            query = query.where(Account.plan_tier == plan_tier)
        if is_suspended is not None:
            query = query.where(Account.is_suspended == is_suspended)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = self.db.execute(count_query).scalar_one()

        # Paginate
        query = query.order_by(Account.created_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)
        accounts = list(self.db.execute(query).scalars().all())

        # Get user counts per account
        account_ids = [a.id for a in accounts]
        user_counts: dict[uuid.UUID, int] = {}
        if account_ids:
            rows = self.db.execute(
                select(User.account_id, func.count())
                .where(User.account_id.in_(account_ids), User.is_active.is_(True), User.deleted_at.is_(None))
                .group_by(User.account_id)
            ).all()
            user_counts = {row[0]: row[1] for row in rows}

        return {
            "accounts": [
                {
                    "id": str(a.id),
                    "name": a.name,
                    "plan_tier": a.plan_tier,
                    "is_suspended": a.is_suspended,
                    "subscription_status": a.subscription_status,
                    "user_count": user_counts.get(a.id, 0),
                    "created_at": a.created_at.isoformat(),
                    "updated_at": a.updated_at.isoformat(),
                }
                for a in accounts
            ],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page if per_page > 0 else 0,
            },
        }

    def get_account(self, account_id: uuid.UUID) -> dict[str, Any]:
        """Get detailed account information."""
        account = self.db.execute(
            select(Account).where(Account.id == account_id, Account.deleted_at.is_(None))
        ).scalar_one_or_none()
        if account is None:
            raise AdminServiceError("Account not found.", "not_found", 404)

        user_count = self.db.execute(
            select(func.count())
            .select_from(User)
            .where(User.account_id == account_id, User.is_active.is_(True), User.deleted_at.is_(None))
        ).scalar_one()

        return {
            "id": str(account.id),
            "name": account.name,
            "plan_tier": account.plan_tier,
            "is_suspended": account.is_suspended,
            "subscription_status": account.subscription_status,
            "stripe_customer_id": account.stripe_customer_id,
            "user_count": user_count,
            "created_at": account.created_at.isoformat(),
            "updated_at": account.updated_at.isoformat(),
        }

    def suspend_account(
        self, account_id: uuid.UUID, *, admin_id: uuid.UUID, ip_address: str | None = None
    ) -> dict[str, Any]:
        """Suspend an account."""
        account = self.db.execute(
            select(Account).where(Account.id == account_id, Account.deleted_at.is_(None))
        ).scalar_one_or_none()
        if account is None:
            raise AdminServiceError("Account not found.", "not_found", 404)
        if account.is_suspended:
            raise AdminServiceError("Account is already suspended.", "conflict", 409)

        account.is_suspended = True
        log_admin_audit(
            self.db,
            admin_id=admin_id,
            action="account.suspended",
            target_type="account",
            target_id=account_id,
            description=f"Suspended account '{account.name}'",
            ip_address=ip_address,
        )
        self.db.commit()

        logger.info("account_suspended", account_id=str(account_id), admin_id=str(admin_id))
        return self.get_account(account_id)

    def unsuspend_account(
        self, account_id: uuid.UUID, *, admin_id: uuid.UUID, ip_address: str | None = None
    ) -> dict[str, Any]:
        """Unsuspend an account."""
        account = self.db.execute(
            select(Account).where(Account.id == account_id, Account.deleted_at.is_(None))
        ).scalar_one_or_none()
        if account is None:
            raise AdminServiceError("Account not found.", "not_found", 404)
        if not account.is_suspended:
            raise AdminServiceError("Account is not suspended.", "conflict", 409)

        account.is_suspended = False
        log_admin_audit(
            self.db,
            admin_id=admin_id,
            action="account.unsuspended",
            target_type="account",
            target_id=account_id,
            description=f"Unsuspended account '{account.name}'",
            ip_address=ip_address,
        )
        self.db.commit()

        logger.info("account_unsuspended", account_id=str(account_id), admin_id=str(admin_id))
        return self.get_account(account_id)

    def update_account_plan(
        self,
        account_id: uuid.UUID,
        plan_tier: str,
        *,
        admin_id: uuid.UUID,
        ip_address: str | None = None,
    ) -> dict[str, Any]:
        """Change an account's plan tier."""
        if plan_tier not in (PlanTier.FREE, PlanTier.PAID):
            raise AdminServiceError("Invalid plan tier.", "bad_request", 400)

        account = self.db.execute(
            select(Account).where(Account.id == account_id, Account.deleted_at.is_(None))
        ).scalar_one_or_none()
        if account is None:
            raise AdminServiceError("Account not found.", "not_found", 404)

        old_tier = account.plan_tier
        if old_tier == plan_tier:
            raise AdminServiceError(f"Account is already on {plan_tier} plan.", "conflict", 409)

        account.plan_tier = plan_tier
        log_admin_audit(
            self.db,
            admin_id=admin_id,
            action="account.plan_changed",
            target_type="account",
            target_id=account_id,
            changes={"plan_tier": {"old": old_tier, "new": plan_tier}},
            description=f"Changed plan from {old_tier} to {plan_tier}",
            ip_address=ip_address,
        )
        self.db.commit()

        logger.info("account_plan_changed", account_id=str(account_id), old=old_tier, new=plan_tier)
        return self.get_account(account_id)

    # ── Users ───────────────────────────────────────────────────────

    def list_users(
        self,
        *,
        page: int = 1,
        per_page: int = 25,
        search: str | None = None,
        account_id: uuid.UUID | None = None,
        is_platform_admin: bool | None = None,
    ) -> dict[str, Any]:
        """List all users with pagination and filters."""
        query = select(User).where(User.deleted_at.is_(None))

        if search:
            query = query.where(
                (User.email.ilike(f"%{search}%")) | (User.name.ilike(f"%{search}%"))
            )
        if account_id:
            query = query.where(User.account_id == account_id)
        if is_platform_admin is not None:
            query = query.where(User.is_platform_admin == is_platform_admin)

        count_query = select(func.count()).select_from(query.subquery())
        total = self.db.execute(count_query).scalar_one()

        query = query.order_by(User.created_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)
        users = list(self.db.execute(query).scalars().all())

        return {
            "users": [self._serialize_user(u) for u in users],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page if per_page > 0 else 0,
            },
        }

    def get_user(self, user_id: uuid.UUID) -> dict[str, Any]:
        """Get detailed user information."""
        user = self.db.execute(
            select(User).where(User.id == user_id, User.deleted_at.is_(None))
        ).scalar_one_or_none()
        if user is None:
            raise AdminServiceError("User not found.", "not_found", 404)
        return self._serialize_user(user)

    def reset_user_password(
        self,
        user_id: uuid.UUID,
        *,
        admin_id: uuid.UUID,
        ip_address: str | None = None,
    ) -> dict[str, Any]:
        """Generate a secure password reset token for a user."""
        user = self.db.execute(
            select(User).where(User.id == user_id, User.deleted_at.is_(None))
        ).scalar_one_or_none()
        if user is None:
            raise AdminServiceError("User not found.", "not_found", 404)

        token = secrets.token_urlsafe(32)
        user.reset_token = token
        user.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)

        log_admin_audit(
            self.db,
            admin_id=admin_id,
            action="user.password_reset_initiated",
            target_type="user",
            target_id=user_id,
            description=f"Initiated password reset for {user.email}",
            ip_address=ip_address,
        )
        self.db.commit()

        logger.info("admin_password_reset", user_id=str(user_id), admin_id=str(admin_id))
        return {
            "reset_token": token,
            "expires_at": user.reset_token_expires.isoformat(),
            "user_email": user.email,
        }

    def toggle_platform_admin(
        self,
        user_id: uuid.UUID,
        *,
        admin_id: uuid.UUID,
        ip_address: str | None = None,
    ) -> dict[str, Any]:
        """Promote or demote a user as platform admin."""
        user = self.db.execute(
            select(User).where(User.id == user_id, User.deleted_at.is_(None))
        ).scalar_one_or_none()
        if user is None:
            raise AdminServiceError("User not found.", "not_found", 404)

        # Demoting: ensure at least one admin remains
        if user.is_platform_admin:
            admin_count = self.db.execute(
                select(func.count())
                .select_from(User)
                .where(User.is_platform_admin.is_(True), User.is_active.is_(True), User.deleted_at.is_(None))
            ).scalar_one()
            if admin_count <= 1:
                raise AdminServiceError(
                    "Cannot demote the last platform admin.", "conflict", 409
                )

        new_status = not user.is_platform_admin
        user.is_platform_admin = new_status
        action = "user.promoted_to_admin" if new_status else "user.demoted_from_admin"

        log_admin_audit(
            self.db,
            admin_id=admin_id,
            action=action,
            target_type="user",
            target_id=user_id,
            changes={"is_platform_admin": {"old": not new_status, "new": new_status}},
            description=f"{'Promoted' if new_status else 'Demoted'} {user.email} {'to' if new_status else 'from'} platform admin",
            ip_address=ip_address,
        )
        self.db.commit()

        logger.info("admin_toggle", user_id=str(user_id), new_status=new_status, admin_id=str(admin_id))
        return self._serialize_user(user)

    # ── Impersonation ───────────────────────────────────────────────

    def impersonate_user(
        self,
        user_id: uuid.UUID,
        *,
        admin_id: uuid.UUID,
        ip_address: str | None = None,
    ) -> dict[str, str]:
        """Generate an impersonation token for a user.

        The token includes an `impersonating` claim so the frontend
        can show an admin banner and the backend can distinguish
        impersonated sessions.
        """
        user = self.db.execute(
            select(User).where(User.id == user_id, User.deleted_at.is_(None))
        ).scalar_one_or_none()
        if user is None:
            raise AdminServiceError("User not found.", "not_found", 404)
        if not user.is_active:
            raise AdminServiceError("Cannot impersonate an inactive user.", "bad_request", 400)
        if user.is_platform_admin:
            raise AdminServiceError("Cannot impersonate another platform admin.", "forbidden", 403)

        identity = str(user.id)
        additional_claims = {
            "account_id": str(user.account_id),
            "role": user.role,
            "is_platform_admin": False,
            "impersonating": True,
            "impersonator_id": str(admin_id),
        }
        access_token = create_access_token(
            identity=identity,
            additional_claims=additional_claims,
            expires_delta=timedelta(hours=1),
        )

        log_admin_audit(
            self.db,
            admin_id=admin_id,
            action="user.impersonated",
            target_type="user",
            target_id=user_id,
            description=f"Started impersonation of {user.email}",
            ip_address=ip_address,
        )
        self.db.commit()

        logger.info("impersonation_started", target_user_id=str(user_id), admin_id=str(admin_id))
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": self._serialize_user(user),
        }

    # ── Metrics ─────────────────────────────────────────────────────

    def get_platform_metrics(self) -> dict[str, Any]:
        """Get high-level platform metrics for the admin dashboard."""
        total_accounts = self.db.execute(
            select(func.count()).select_from(Account).where(Account.deleted_at.is_(None))
        ).scalar_one()

        active_accounts = self.db.execute(
            select(func.count())
            .select_from(Account)
            .where(Account.deleted_at.is_(None), Account.is_suspended.is_(False))
        ).scalar_one()

        suspended_accounts = self.db.execute(
            select(func.count())
            .select_from(Account)
            .where(Account.deleted_at.is_(None), Account.is_suspended.is_(True))
        ).scalar_one()

        total_users = self.db.execute(
            select(func.count()).select_from(User).where(User.deleted_at.is_(None))
        ).scalar_one()

        active_users = self.db.execute(
            select(func.count())
            .select_from(User)
            .where(User.deleted_at.is_(None), User.is_active.is_(True))
        ).scalar_one()

        free_accounts = self.db.execute(
            select(func.count())
            .select_from(Account)
            .where(Account.deleted_at.is_(None), Account.plan_tier == PlanTier.FREE)
        ).scalar_one()

        paid_accounts = self.db.execute(
            select(func.count())
            .select_from(Account)
            .where(Account.deleted_at.is_(None), Account.plan_tier == PlanTier.PAID)
        ).scalar_one()

        # MRR: $29.99/mo per paid account
        mrr = paid_accounts * 29.99

        # Recent signups (last 30 days)
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        recent_signups = self.db.execute(
            select(func.count())
            .select_from(Account)
            .where(Account.deleted_at.is_(None), Account.created_at >= thirty_days_ago)
        ).scalar_one()

        return {
            "total_accounts": total_accounts,
            "active_accounts": active_accounts,
            "suspended_accounts": suspended_accounts,
            "total_users": total_users,
            "active_users": active_users,
            "free_accounts": free_accounts,
            "paid_accounts": paid_accounts,
            "mrr": round(mrr, 2),
            "recent_signups": recent_signups,
        }

    # ── Audit Logs ──────────────────────────────────────────────────

    def list_audit_logs(
        self,
        *,
        page: int = 1,
        per_page: int = 50,
        admin_id: uuid.UUID | None = None,
        action: str | None = None,
    ) -> dict[str, Any]:
        """List admin audit logs with pagination."""
        query = select(AdminAuditLog)

        if admin_id:
            query = query.where(AdminAuditLog.admin_id == admin_id)
        if action:
            query = query.where(AdminAuditLog.action == action)

        count_query = select(func.count()).select_from(query.subquery())
        total = self.db.execute(count_query).scalar_one()

        query = query.order_by(AdminAuditLog.timestamp.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)
        logs = list(self.db.execute(query).scalars().all())

        return {
            "logs": [
                {
                    "id": str(log.id),
                    "admin_id": str(log.admin_id),
                    "action": log.action,
                    "target_type": log.target_type,
                    "target_id": str(log.target_id) if log.target_id else None,
                    "changes": log.changes,
                    "description": log.description,
                    "ip_address": log.ip_address,
                    "timestamp": log.timestamp.isoformat(),
                }
                for log in logs
            ],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page if per_page > 0 else 0,
            },
        }

    # ── Helpers ─────────────────────────────────────────────────────

    def _serialize_user(self, user: User) -> dict[str, Any]:
        """Serialize a User to a dict for API responses."""
        return {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "account_id": str(user.account_id),
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "is_platform_admin": user.is_platform_admin,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
        }
