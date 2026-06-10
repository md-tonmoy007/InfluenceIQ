from __future__ import annotations

from scoring_service.analysis.bot_behavior import score_bot_behavior
from scoring_service.analysis.coordinated_engagement import score_coordinated_engagement
from scoring_service.analysis.credibility import calculate_credibility
from scoring_service.analysis.fake_comment import score_fake_comments
from scoring_service.analysis.fake_engagement import analyze_fake_engagement
from scoring_service.analysis.fake_follower import score_fake_followers

__all__ = ["analyze_fake_engagement", "calculate_credibility", "score_bot_behavior",
           "score_coordinated_engagement", "score_fake_comments", "score_fake_followers"]
