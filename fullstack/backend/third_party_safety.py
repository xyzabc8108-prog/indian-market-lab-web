"""Third-party public content rights safeguards.

A service link is not permission to copy third-party content onto our pages.
Keep the public headline aggregation disabled without written permissions and
product-specific service-terms review. Neither environment flag proves rights.
"""
import os

NEWS_FEED_PAUSED_NOTICE = (
    "Automatic public republication of Google News RSS headlines is paused "
    "pending verification of Google News and original-publisher content rights. "
    "Use the official source links instead; news is not a prediction."
)


def public_headline_feed_enabled() -> bool:
    return (
        os.environ.get("IML_PUBLIC_NEWS_FEED_ENABLED", "").strip().lower() == "true"
        and os.environ.get("IML_NEWS_REDISPLAY_RIGHTS_VERIFIED", "").strip().lower() == "true"
    )
