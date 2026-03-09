"""Account and team management service layer."""

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from services.auth.models.models import Account, TeamInvite, TeamRole, User
from services.auth.repositories.auth_repository import (
    AccountRepository,
    RefreshTokenRepository,
    TeamInviteRepository,
    UserRepository,
)
from services.auth.services.auth_service import AuthServiceError
from services.shared.audit import log_audit
from services.shared.events import EventPublisher
from services.shared.logging import get_logger

logger = get_logger("account_service")


class AccountService:
    """Account and team management operations."""

    def __init__(
        self,
        db: Session,
        event_publisher: EventPublisher | None = None,
    ) -> None:
        self.db = db
        self.user_repo = UserRepository(db)
        self.account_repo = AccountRepository(db)
        self.token_repo = RefreshTokenRepository(db)
        self.invite_repo = TeamInviteRepository(db)
        self.event_publisher = event_publisher

    # ── Account Management ──────────────────────────────────────────

    def get_account(self, account_id: uuid.UUID) -> dict[str, Any]:
        """Get account details including member count.

        Raises:
            AuthServiceError: If account not found.
        """
        account = self.account_repo.get_by_id(account_id)
        if account is None:
            raise AuthServiceError("Account not found.", "not_found", 404)

        member_count = self.user_repo.count_active_members(account_id)
        return {
            "id": str(account.id),
            "name": account.name,
            "plan_tier": account.plan_tier,
            "member_count": member_count,
            "created_at": account.created_at.isoformat(),
        }

    def update_account(
        self, account_id: uuid.UUID, actor_id: uuid.UUID, name: str
    ) -> dict[str, Any]:
        """Update account details. Only owners and admins can do this.

        Raises:
            AuthServiceError: If account not found.
        """
        account = self.account_repo.get_by_id(account_id)
        if account is None:
            raise AuthServiceError("Account not found.", "not_found", 404)

        old_name = account.name
        account.name = name
        self.account_repo.save()

        log_audit(
            self.db,
            account_id=account_id,
            actor_id=actor_id,
            action="update",
            resource_type="accounts",
            resource_id=account.id,
            changes={"name": {"old": old_name, "new": name}},
        )
        self.db.commit()

        member_count = self.user_repo.count_active_members(account_id)
        return {
            "id": str(account.id),
            "name": account.name,
            "plan_tier": account.plan_tier,
            "member_count": member_count,
            "created_at": account.created_at.isoformat(),
        }

    def delete_account(self, account_id: uuid.UUID, actor_id: uuid.UUID) -> None:
        """Soft-delete an account and all its users.

        Raises:
            AuthServiceError: If account not found or actor is not the owner.
        """
        actor = self.user_repo.get_by_id(actor_id)
        if actor is None or actor.role != TeamRole.OWNER:
            raise AuthServiceError("Only account owners can delete the account.", "forbidden", 403)

        account = self.account_repo.get_by_id(account_id)
        if account is None:
            raise AuthServiceError("Account not found.", "not_found", 404)

        now = datetime.now(timezone.utc)
        account.deleted_at = now

        # Deactivate and soft-delete all users
        users = self.user_repo.list_by_account(account_id, include_inactive=True)
        for user in users:
            user.is_active = False
            user.deleted_at = now
            self.token_repo.revoke_all_for_user(user.id)

        log_audit(
            self.db,
            account_id=account_id,
            actor_id=actor_id,
            action="delete",
            resource_type="accounts",
            resource_id=account.id,
        )
        self.db.commit()

        self._publish_event("account.deleted", {
            "account_id": str(account_id),
            "deleted_by": str(actor_id),
        })

    # ── Team Management ─────────────────────────────────────────────

    def list_members(self, account_id: uuid.UUID) -> list[dict[str, Any]]:
        """List all active team members."""
        users = self.user_repo.list_by_account(account_id)
        return [
            {
                "id": str(u.id),
                "email": u.email,
                "name": u.name,
                "role": u.role,
                "is_verified": u.is_verified,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat(),
            }
            for u in users
        ]

    def invite_member(
        self,
        account_id: uuid.UUID,
        actor_id: uuid.UUID,
        email: str,
        role: str = TeamRole.MEMBER,
    ) -> dict[str, Any]:
        """Invite a new team member by email.

        Raises:
            AuthServiceError: On permission, plan limit, or duplicate invite issues.
        """
        actor = self.user_repo.get_by_id(actor_id)
        if actor is None:
            raise AuthServiceError("Actor not found.", "not_found", 404)
        if actor.role not in (TeamRole.OWNER, TeamRole.ADMIN):
            raise AuthServiceError("Only owners and admins can invite team members.", "forbidden", 403)

        # Check plan limits
        account = self.account_repo.get_by_id(account_id)
        if account is None:
            raise AuthServiceError("Account not found.", "not_found", 404)

        current_count = self.user_repo.count_active_members(account_id)
        pending_invites = self.invite_repo.list_by_account(account_id, pending_only=True)
        total = current_count + len(pending_invites)

        if total >= account.team_member_limit:
            raise AuthServiceError(
                f"Team member limit reached for {account.plan_tier} plan.",
                "forbidden",
                403,
            )

        # Check for existing user or pending invite
        existing_user = self.user_repo.get_by_email(email)
        if existing_user is not None and existing_user.account_id == account_id:
            raise AuthServiceError("User is already a member of this account.", "conflict", 409)

        existing_invite = self.invite_repo.get_pending_by_email_and_account(email, account_id)
        if existing_invite is not None:
            raise AuthServiceError("An invitation has already been sent to this email.", "conflict", 409)

        invite = TeamInvite(
            account_id=account_id,
            email=email,
            role=role,
            invited_by=actor_id,
            token=secrets.token_urlsafe(32),
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        self.invite_repo.create(invite)

        log_audit(
            self.db,
            account_id=account_id,
            actor_id=actor_id,
            action="create",
            resource_type="team_invites",
            resource_id=invite.id,
            changes={"email": email, "role": role},
        )
        self.db.commit()

        self._publish_event("team.member.invited", {
            "account_id": str(account_id),
            "email": email,
            "role": role,
            "invited_by": str(actor_id),
        })

        # TODO: Send actual invitation email (Phase 2)
        logger.info("team_member_invited", account_id=str(account_id), email=email)

        return {
            "id": str(invite.id),
            "email": invite.email,
            "role": invite.role,
            "expires_at": invite.expires_at.isoformat(),
        }

    def update_member_role(
        self,
        account_id: uuid.UUID,
        actor_id: uuid.UUID,
        member_id: uuid.UUID,
        new_role: str,
    ) -> dict[str, Any]:
        """Update a team member's role. Only owners can promote/demote admins.

        Raises:
            AuthServiceError: On permission or validation issues.
        """
        actor = self.user_repo.get_by_id(actor_id)
        if actor is None or actor.role != TeamRole.OWNER:
            raise AuthServiceError("Only account owners can change member roles.", "forbidden", 403)

        member = self.user_repo.get_by_id(member_id)
        if member is None or member.account_id != account_id:
            raise AuthServiceError("Member not found.", "not_found", 404)

        if member.id == actor_id:
            raise AuthServiceError("Cannot change your own role.", "bad_request", 400)

        old_role = member.role
        member.role = new_role
        self.user_repo.save()

        log_audit(
            self.db,
            account_id=account_id,
            actor_id=actor_id,
            action="update",
            resource_type="users",
            resource_id=member.id,
            changes={"role": {"old": old_role, "new": new_role}},
        )
        self.db.commit()

        self._publish_event("team.member.role_changed", {
            "account_id": str(account_id),
            "user_id": str(member.id),
            "old_role": old_role,
            "new_role": new_role,
        })

        return {
            "id": str(member.id),
            "email": member.email,
            "name": member.name,
            "role": member.role,
            "is_active": member.is_active,
        }

    def remove_member(
        self,
        account_id: uuid.UUID,
        actor_id: uuid.UUID,
        member_id: uuid.UUID,
    ) -> None:
        """Remove (deactivate) a team member and revoke their tokens.

        Raises:
            AuthServiceError: On permission or validation issues.
        """
        actor = self.user_repo.get_by_id(actor_id)
        if actor is None:
            raise AuthServiceError("Actor not found.", "not_found", 404)
        if actor.role not in (TeamRole.OWNER, TeamRole.ADMIN):
            raise AuthServiceError("Only owners and admins can remove team members.", "forbidden", 403)

        member = self.user_repo.get_by_id(member_id)
        if member is None or member.account_id != account_id:
            raise AuthServiceError("Member not found.", "not_found", 404)

        if member.id == actor_id:
            raise AuthServiceError("Cannot remove yourself.", "bad_request", 400)

        if member.role == TeamRole.OWNER:
            raise AuthServiceError("Cannot remove the account owner.", "forbidden", 403)

        # Admins cannot remove other admins
        if actor.role == TeamRole.ADMIN and member.role == TeamRole.ADMIN:
            raise AuthServiceError("Admins cannot remove other admins.", "forbidden", 403)

        member.is_active = False
        self.user_repo.save()
        self.token_repo.revoke_all_for_user(member.id)

        log_audit(
            self.db,
            account_id=account_id,
            actor_id=actor_id,
            action="delete",
            resource_type="users",
            resource_id=member.id,
        )
        self.db.commit()

        self._publish_event("team.member.removed", {
            "account_id": str(account_id),
            "user_id": str(member.id),
            "removed_by": str(actor_id),
        })

    # ── User Profile ────────────────────────────────────────────────

    def get_profile(self, user_id: uuid.UUID) -> dict[str, Any]:
        """Get a user's profile."""
        user = self.user_repo.get_by_id(user_id)
        if user is None:
            raise AuthServiceError("User not found.", "not_found", 404)

        return {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "is_verified": user.is_verified,
            "account_id": str(user.account_id),
            "created_at": user.created_at.isoformat(),
        }

    def update_profile(
        self,
        user_id: uuid.UUID,
        account_id: uuid.UUID,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """Update a user's profile. If email changes, require re-verification.

        Raises:
            AuthServiceError: If user not found or email already taken.
        """
        user = self.user_repo.get_by_id(user_id)
        if user is None:
            raise AuthServiceError("User not found.", "not_found", 404)

        changes: dict[str, Any] = {}

        if "name" in updates:
            changes["name"] = {"old": user.name, "new": updates["name"]}
            user.name = updates["name"]

        if "email" in updates and updates["email"] != user.email:
            existing = self.user_repo.get_by_email(updates["email"])
            if existing is not None:
                raise AuthServiceError("Email already in use.", "conflict", 409)
            changes["email"] = {"old": user.email, "new": updates["email"]}
            user.email = updates["email"]
            user.is_verified = False
            user.verification_token = secrets.token_urlsafe(32)
            user.verification_token_expires = datetime.now(timezone.utc) + timedelta(hours=24)
            # TODO: Send verification email (Phase 2)

        self.user_repo.save()

        if changes:
            log_audit(
                self.db,
                account_id=account_id,
                actor_id=user_id,
                action="update",
                resource_type="users",
                resource_id=user.id,
                changes=changes,
            )

        self.db.commit()

        return {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "is_verified": user.is_verified,
            "account_id": str(user.account_id),
            "created_at": user.created_at.isoformat(),
        }

    # ── Helpers ─────────────────────────────────────────────────────

    def _publish_event(self, event_type: str, payload: dict[str, Any]) -> None:
        """Publish an event to Redis Pub/Sub if publisher is available."""
        if self.event_publisher is not None:
            self.event_publisher.publish(event_type, payload, source_service="auth")
