from backend.pipeline.analysis.reason_builder import build_summary
from backend.pipeline.fusion.fusion import fuse as fuse_layers
from backend.pipeline.fusion.sub_scores import build_influencer_output, build_role5_scores
from backend.pipeline.fusion.trust import calculate_role5_trust
from backend.pipeline.fusion.versioning import (
    MODEL_VERSION,
    MODEL_VERSION_ALIAS,
    MODEL_VERSION_V2,
    model_version_for,
)


def test_renormalized_fusion_and_missing_layer() -> None:
    """The new dataclass-based fusion recognises the ``graph_proxy`` key
    and renames-drop the previous ``graph`` key (now an unknown layer
    that the fusion silently ignores)."""
    fusion = fuse_layers({"semantic": 80, "behavioral": 60, "graph_proxy": None, "bot_rings": 40, "brand_safety": 20})
    payload = fusion.as_dict()
    assert fusion.renormalized
    assert not fusion.components["graph_proxy"]["available"]
    assert round(sum(item["weight"] for item in fusion.components.values()), 3) == 1
    # The as_dict() surface is dict-shaped for legacy consumers.
    assert payload["renormalized"] is True
    assert "graph_proxy" in payload["missing_layers"]


def test_trust_formula_and_caps() -> None:
    base = {"relevance_score": 100, "credibility_score": 100, "engagement_quality_score": 100,
            "sentiment_score": 100, "brand_safety_score": 100, "source_confidence_score": 100,
            "overall_fake_risk_score": 0}
    assert calculate_role5_trust(base, data_source_count=6).role5_trust_score == 100
    assert calculate_role5_trust({**base, "overall_fake_risk_score": 90}, data_source_count=6).role5_trust_score <= 45
    assert calculate_role5_trust(base, data_source_count=1).role5_trust_score == 70
    assert calculate_role5_trust(base, data_source_count=6, severe_brand_safety=True).role5_trust_score == 40


def test_model_version_helper_v2_when_any_v2_layer_used() -> None:
    """The model_version_for helper returns MODEL_VERSION_V2 when any
    v2 adapter fires and MODEL_VERSION otherwise. The LLM explainer is
    intentionally excluded from the bump."""
    assert model_version_for(semantic_v2=False, behavioral_v2=False,
                             graph_v2=False, bot_rings_v2=False) == MODEL_VERSION
    assert model_version_for(semantic_v2=True, behavioral_v2=False,
                             graph_v2=False, bot_rings_v2=False) == MODEL_VERSION_V2
    assert model_version_for(semantic_v2=False, behavioral_v2=True,
                             graph_v2=False, bot_rings_v2=False) == MODEL_VERSION_V2
    # The v1 alias is still the historical string.
    assert MODEL_VERSION_ALIAS == "Role5-FakeSignal-v1"
    assert MODEL_VERSION_V2 == "Role5-FakeDetectionScore-v2"


def test_full_output_contract_and_reasons() -> None:
    candidate = {"influencer_id": "i-1", "name": "Dr Sarah Tan", "credentials": ["MD"],
        "professional_titles": ["doctor"], "authority_mentions": ["university"], "data_source_count": 4,
        "bio": "Helpful professional nutrition education", "bio_present": True, "profile_picture_present": True,
        "comments": ["Helpful authentic advice", "Great post"], "follower_count": 10000, "following_count": 500,
        "engagement_rate": 0.02, "diverse_comments_score": 1, "context_relevant_comments_score": 1}
    scores = build_role5_scores(candidate)
    output = build_influencer_output(candidate)
    assert scores["sub_scores"]["role5_trust_score"] >= 0
    assert output["risk_score"]["model_version"] in (MODEL_VERSION, MODEL_VERSION_ALIAS)
    assert output["positive_reasons"] and output["explanation"]
    assert "classified" in build_summary("B", "Medium", ["Credential found"], [], "SAFE")
