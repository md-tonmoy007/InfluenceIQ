from umgl_ai.final_risk import evaluate


def test_evaluate_renormalises_when_signal_missing() -> None:
    decision = evaluate(
        {
            "semantic":  (0.9, 0.3),
            "behavior":  (-1.0, 0.25),  # missing
            "graph":     (0.4, 0.25),
            "cluster":   (0.2, 0.2),
        }
    )
    assert "behavior" in decision.missing_signals
    # weights must sum to 1 after renormalisation
    assert abs(sum(decision.effective_weights.values()) - 1.0) < 1e-6
    # renormalised ensemble should sit between the lowest and highest input
    assert 0.2 <= decision.risk_score <= 0.9


def test_evaluate_classifies_extreme_signals() -> None:
    bot = evaluate(
        {"semantic": (0.95, 0.3), "behavior": (0.92, 0.25), "graph": (0.9, 0.25), "cluster": (0.95, 0.2)}
    )
    safe = evaluate(
        {"semantic": (0.05, 0.3), "behavior": (0.05, 0.25), "graph": (0.05, 0.25), "cluster": (0.05, 0.2)}
    )
    assert bot.category in {"BOT", "SPAM_RING"}
    assert safe.category == "SAFE"


def test_evaluate_handles_all_signals_missing() -> None:
    decision = evaluate({k: (-1.0, w) for k, w in {"semantic": 0.3, "behavior": 0.25, "graph": 0.25, "cluster": 0.2}.items()})
    assert decision.risk_score == 0.0
    assert decision.category == "SAFE"
    assert set(decision.missing_signals) == {"semantic", "behavior", "graph", "cluster"}
