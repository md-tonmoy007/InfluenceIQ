from backend.pipeline.identity.resolver import resolve_candidates, resolve_identity_clusters


def test_url_hash_and_fuzzy_merges() -> None:
    exact = resolve_candidates(
        {"name": "Dr Sarah Tan", "platforms": {"instagram": "https://instagram.com/drsarahtan/"}},
        {"name": "Sarah Tan MD", "platforms": {"instagram": "https://www.instagram.com/drsarahtan"}},
    )
    assert exact["merge"] and exact["strategy"] == "profile_url"
    fuzzy = resolve_candidates(
        {"name": "Sarah Tan", "platforms": {"instagram": "@sarahtan"}},
        {"name": "Dr Sarah Tan", "platforms": {"youtube": "@sarahtan"}},
    )
    assert fuzzy["merge"] and fuzzy["confidence"] >= 0.90


def test_ambiguous_handoff_and_merge_event() -> None:
    ambiguous = resolve_candidates({"name": "Maya Green"}, {"name": "Maya Grant"})
    assert not ambiguous["merge"] and ambiguous["requires_llm"]
    emitted = []
    result = resolve_identity_clusters([
        {"mention_id": "a", "name": "Sarah Tan", "source_url": "https://a", "platforms": {"instagram": "@sarahtan"}},
        {"mention_id": "b", "name": "Dr Sarah Tan", "source_url": "https://b", "platforms": {"youtube": "@sarahtan"}},
    ], campaign_id="c", event_emitter=lambda *args: emitted.append(args))
    assert len(result["canonical"]) == 1
    assert result["merge_events"][0]["merged_from"] == ["a", "b"]
    assert emitted[0][1] == "identity.merged"
