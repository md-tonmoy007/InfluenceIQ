"""Embedding env wiring tests for plan 06.

Covers the three scenarios in plan 06 §5.2:

1. OPENROUTER_API_KEY absent → both
   :func:`compute_and_persist_embedding` and
   :func:`compute_and_persist_campaign_embedding` write envelopes with
   ``source="openrouter"`` and a deterministic hash-derived stub vector
   (L2-normalized, length ``EMBEDDING_DIM``).  The relevance scorer
   then runs cosine on both stubs and returns a finite float — never
   the 50.0 token-overlap neutral.
2. OPENROUTER_API_KEY present and OpenRouter returns an embedding →
   envelope still has ``source="openrouter"``, ``model`` equals the
   value of ``UMGL_EMBEDDING_MODEL``.
3. One side missing envelope entirely → :func:`relevance_score` falls
   into the token-overlap path and reads niche + target_audience
   (regression check, same as ``test_sub_scores_relevance.py``).
"""

from __future__ import annotations

import math
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
os.environ.setdefault("REDIS_STATE_DB", "redis://localhost:6379/2")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")


def _fake_session_with(influencer=None, campaign=None):
    """Build a MagicMock session that returns *influencer* / *campaign* from .get()."""
    session = MagicMock()
    session.get.side_effect = lambda model, _id: (
        influencer if model.__name__ == "Influencer" else campaign
    )
    return session


class StubVectorContractTest(unittest.TestCase):
    def test_stub_vector_is_l2_normalized_with_embedding_dim_length(self) -> None:
        from backend.pipeline.content.enrichment import _stub_vector

        vec = _stub_vector("trail running coach")
        self.assertEqual(len(vec), 1536)  # EMBEDDING_DIM default
        norm = math.sqrt(sum(x * x for x in vec))
        self.assertAlmostEqual(norm, 1.0, places=6)

    def test_stub_vector_is_deterministic(self) -> None:
        from backend.pipeline.content.enrichment import _stub_vector

        a = _stub_vector("trail running coach")
        b = _stub_vector("trail running coach")
        self.assertEqual(a, b)

    def test_stub_vector_different_inputs_diverge(self) -> None:
        from backend.pipeline.content.enrichment import _stub_vector

        a = _stub_vector("trail running coach")
        b = _stub_vector("wellness nutrition expert")
        # They should not be identical
        self.assertNotEqual(a, b)


class ComputeAndPersistWiringTest(unittest.TestCase):
    def setUp(self) -> None:
        os.environ.pop("OPENROUTER_API_KEY", None)
        os.environ["UMGL_EMBEDDING_MODEL"] = "text-embedding-3-small"
        os.environ["EMBEDDING_DIM"] = "1536"

    def test_influencer_helper_writes_stub_envelope_when_key_absent(self) -> None:
        from backend.core.database import models
        from backend.pipeline.content.enrichment import (
            _build_influencer_embedding_text,
            compute_and_persist_embedding,
        )
        from backend.pipeline.fusion.sub_scores import relevance_score

        influencer = MagicMock(spec=models.Influencer)
        influencer.id = "inf-1"
        influencer.bio = "Trail running coach and outdoor athlete"
        influencer.display_name = "Trail Coach"
        influencer.embedding = None

        session = _fake_session_with(influencer=influencer)
        # The helper calls session.query(models.PlatformProfile).filter(...).all()
        # — return an empty list so the corpus builder short-circuits and
        # we use the (mocked) influencer's bio/display_name via the helper.
        # But the helper does NOT read influencer.bio directly — it queries
        # the DB. So we patch _build_influencer_embedding_text to return
        # a known string.
        with patch(
            "backend.pipeline.content.enrichment._build_influencer_embedding_text",
            return_value="trail running coach outdoor athlete",
        ):
            envelope = compute_and_persist_embedding(session, influencer.id)

        self.assertIsNotNone(envelope)
        self.assertEqual(envelope["source"], "openrouter")
        self.assertEqual(envelope["model"], "text-embedding-3-small")
        self.assertEqual(len(envelope["vector"]), 1536)

        # Storing the envelope on the influencer mock
        self.assertEqual(influencer.embedding["source"], "openrouter")

        # The relevance scorer should run cosine (not token overlap) on
        # two stub envelopes, returning a finite float that is NOT 50.0
        # neutral. The stub vectors are L2-normalized hashes of
        # different texts, so cosine will be small-but-nonzero.
        score = relevance_score(
            {"embedding": envelope},
            {"embedding": envelope},
        )
        self.assertTrue(math.isfinite(score))
        self.assertNotEqual(score, 50.0)

    def test_campaign_helper_writes_stub_envelope_when_key_absent(self) -> None:
        from backend.core.database import models
        from backend.pipeline.content.enrichment import (
            compute_and_persist_campaign_embedding,
        )

        campaign = MagicMock(spec=models.Campaign)
        campaign.id = "camp-1"
        campaign.niche = "wellness"
        campaign.target_audience = "fitness enthusiasts"
        campaign.goals = "increase brand awareness"
        campaign.product = "supplements"
        campaign.search_query = "fitness creators"
        campaign.embedding = None

        session = _fake_session_with(campaign=campaign)
        envelope = compute_and_persist_campaign_embedding(session, campaign.id)

        self.assertIsNotNone(envelope)
        self.assertEqual(envelope["source"], "openrouter")
        self.assertEqual(envelope["model"], "text-embedding-3-small")
        self.assertEqual(len(envelope["vector"]), 1536)
        self.assertEqual(campaign.embedding["source"], "openrouter")

    def test_influencer_helper_uses_openrouter_model_from_env(self) -> None:
        from backend.core.database import models
        from backend.pipeline.content.enrichment import compute_and_persist_embedding

        influencer = MagicMock(spec=models.Influencer)
        influencer.id = "inf-2"
        influencer.embedding = None

        session = _fake_session_with(influencer=influencer)
        with patch(
            "backend.pipeline.content.enrichment._build_influencer_embedding_text",
            return_value="outdoor adventure guide",
        ), patch.dict(
            os.environ, {"UMGL_EMBEDDING_MODEL": "text-embedding-3-large", "OPENROUTER_API_KEY": "sk-test"}
        ):
            # Patch the OpenRouter adapter to return a fixed embedding
            # without making a network call.
            with patch(
                "backend.ml.models.openrouter_llm.OpenRouterAdapter.embed_text",
                new_callable=MagicMock,
            ) as mock_embed:
                mock_embed.return_value = [0.1] * 1536
                envelope = compute_and_persist_embedding(session, influencer.id)

        self.assertIsNotNone(envelope)
        self.assertEqual(envelope["source"], "openrouter")
        self.assertEqual(envelope["model"], "text-embedding-3-large")
        self.assertEqual(len(envelope["vector"]), 1536)

    def test_one_side_missing_envelope_falls_back_to_token_overlap(self) -> None:
        from backend.pipeline.fusion.sub_scores import relevance_score

        # Campaign has no envelope at all → token-overlap path runs
        # and reads niche + target_audience from the campaign dict.
        score = relevance_score(
            {"bio": "trail running coach", "context": "", "tags": []},
            {"niche": "trail running", "target_audience": "outdoor athletes"},
        )
        # Token overlap matches niche terms → score above neutral
        self.assertGreater(score, 50.0)


if __name__ == "__main__":
    unittest.main()
