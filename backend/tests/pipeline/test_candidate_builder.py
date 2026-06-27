from __future__ import annotations

from uuid import uuid4

from backend.core.database import models
from backend.pipeline.candidate.builder import build_influencer_candidate
from backend.pipeline.content.enrichment import collect_platform_urls


def test_collect_platform_urls_from_platforms_json():
    influencer = models.Influencer(
        canonical_name="Test Creator",
        platforms={
            "youtube": "https://youtube.com/@testcreator",
            "instagram": "https://instagram.com/testcreator",
        },
    )
    urls = collect_platform_urls(influencer)
    assert "https://youtube.com/@testcreator" in urls
    assert "https://instagram.com/testcreator" in urls


def test_build_candidate_defaults_without_platform_rows():
    class FakeSession:
        def get(self, model, obj_id):
            return models.Influencer(
                id=obj_id,
                canonical_name="Fallback Creator",
                platforms={},
                mentions=[],
            )

        def query(self, *args, **kwargs):
            class Query:
                def filter(self, *a, **k):
                    return self

                def join(self, *a, **k):
                    return self

                def order_by(self, *a, **k):
                    return self

                def limit(self, *a, **k):
                    return self

                def all(self):
                    return []

            return Query()

    influencer_id = uuid4()
    campaign_id = uuid4()
    candidate = build_influencer_candidate(
        FakeSession(),
        influencer_id,
        campaign_id,
        include_platform=False,
    )
    assert candidate["canonical_name"] == "Fallback Creator"
    assert candidate["comments"] == []
