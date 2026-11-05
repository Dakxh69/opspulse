"""
OpsPulse Backend — CLI Management Commands

Provides administrative CLI operations:
- seed-admin: Bootstraps the first administrator from environment variables:
  `FIRST_ADMIN_EMAIL` and `FIRST_ADMIN_PASSWORD`.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_secret
from app.database.session import AsyncSessionLocal
from app.models.user import User, UserRole
from app.services.audit_service import record_audit_log


async def seed_admin() -> int:
    """Bootstraps the first Admin user from environment variables."""
    email = settings.FIRST_ADMIN_EMAIL
    password = settings.FIRST_ADMIN_PASSWORD

    if not email or not password:
        print(
            "Error: FIRST_ADMIN_EMAIL and FIRST_ADMIN_PASSWORD environment variables must be set.",
            file=sys.stderr,
        )
        return 1

    if len(password) < 8:
        print(
            "Error: FIRST_ADMIN_PASSWORD must be at least 8 characters.",
            file=sys.stderr,
        )
        return 1

    async with AsyncSessionLocal() as db:
        # Check if an admin already exists
        stmt = select(User).where(User.role == UserRole.ADMIN)
        result = await db.execute(stmt)
        existing_admin = result.scalars().first()

        if existing_admin is not None:
            print(
                f"Admin user already exists ({existing_admin.email}). Bootstrap aborted.",
                file=sys.stderr,
            )
            return 0

        # Check if email is already taken by another role
        stmt_email = select(User).where(User.email == email)
        res_email = await db.execute(stmt_email)
        existing_user = res_email.scalar_one_or_none()

        if existing_user is not None:
            print(
                f"Error: User with email {email} already exists.",
                file=sys.stderr,
            )
            return 1

        new_admin = User(
            email=email,
            password_hash=hash_secret(password),
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(new_admin)
        await db.commit()
        await db.refresh(new_admin)

        await record_audit_log(
            db,
            action="ADMIN_BOOTSTRAP",
            target_type="user",
            target_id=str(new_admin.id),
            actor_user_id=new_admin.id,
            metadata={"email": new_admin.email},
        )

        print(
            f"Successfully bootstrapped initial admin user: {new_admin.email} (ID: {new_admin.id})"
        )
        return 0


def main() -> None:
    """Entry point for python -m app.cli."""
    parser = argparse.ArgumentParser(description="OpsPulse Backend CLI Utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("seed-admin", help="Bootstrap initial admin account from env vars")

    args = parser.parse_args()

    if args.command == "seed-admin":
        sys.exit(asyncio.run(seed_admin()))


if __name__ == "__main__":
    main()
