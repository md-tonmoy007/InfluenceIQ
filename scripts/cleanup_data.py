from __future__ import annotations

import argparse
import sys

from sqlalchemy.orm import Session

from backend.core.database import models
from backend.core.database.session import _get_session_local

# Tables wiped by the cleanup. Order matters: children must be deleted
# before parents to satisfy foreign-key constraints. Authentication and
# profile tables (User, BrandProfile, NotificationPreference,
# IntegrationConnection, ApiKey, Subscription) are intentionally
# preserved.
CLEANUP_ORDER: list[type[models.Base]] = [
    models.DeepAnalysisReport,
    models.DeepAnalysisPostResult,
    models.DeepAnalysisRun,
    models.PlatformComment,
    models.PlatformPost,
    models.PlatformProfile,
    models.CandidateSnapshot,
    models.IdentityMerge,
    models.SavedListItem,
    models.SavedList,
    models.CampaignContract,
    models.BrandSafetyFlag,
    models.CredentialVerification,
    models.InfluencerScore,
    models.CrawlSourceInfluencer,
    models.CrawlSource,
    models.Influencer,
    models.Campaign,
    models.Brand,
]

PRESERVED: list[str] = [
    "users",
    "brand_profiles",
    "notification_preferences",
    "integration_connections",
    "api_keys",
    "subscriptions",
]


def _count(db: Session, model: type[models.Base]) -> int:
    return db.query(model).count()


def cleanup_data(db: Session, *, verbose: bool = True) -> dict[str, int]:
    """Delete all campaign / influencer data, preserving auth + profile.

    Returns a mapping of ``{table_name: rows_deleted}``. The mapping is
    populated in the same order as :data:`CLEANUP_ORDER`.
    """
    deleted: dict[str, int] = {}
    for model in CLEANUP_ORDER:
        rows = db.query(model).delete(synchronize_session=False)
        deleted[model.__tablename__] = rows
        if verbose:
            print(f"  deleted {rows:>8} from {model.__tablename__}")
    db.commit()
    return deleted


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Wipe all campaign and influencer data from the database. "
            "Authentication and profile tables (users, brand_profiles, "
            "notification_preferences, integration_connections, api_keys, "
            "subscriptions) are preserved."
        )
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Skip the interactive confirmation prompt.",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress per-table delete counts.",
    )
    args = parser.parse_args()

    print("InfluenceIQ data cleanup")
    print("Preserved tables (auth + profile):")
    for name in PRESERVED:
        print(f"  - {name}")
    print("Tables to be wiped:")
    for model in CLEANUP_ORDER:
        print(f"  - {model.__tablename__}")

    if not args.yes:
        answer = input("\nProceed with full cleanup? [y/N] ").strip().lower()
        if answer not in {"y", "yes"}:
            print("Aborted. No changes made.")
            return 0

    db = _get_session_local()()
    try:
        print("\nDeleting rows...")
        deleted = cleanup_data(db, verbose=not args.quiet)
        db.commit()
        total = sum(deleted.values())
        print(f"\nCleanup complete. {total} rows removed across {len(deleted)} tables.")
    except Exception as exc:
        db.rollback()
        print(f"Cleanup failed: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())