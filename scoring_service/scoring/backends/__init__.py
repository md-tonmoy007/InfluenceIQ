"""Optional, feature-flag-gated scoring backends for Role 5.

The :mod:`umgl_ai_adapters` module in this package is the only active
backend in v1 of the upgrade. It mirrors the :mod:`scoring_service.extraction.contact_info`
pattern: module-level environment flags, lazy imports with try/except
fallback, and pure functions that return ``(score, model_versions)``
tuples or empty strings.
"""
