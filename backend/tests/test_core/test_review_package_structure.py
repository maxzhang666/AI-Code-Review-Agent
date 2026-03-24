from __future__ import annotations

import importlib


def test_review_module_is_a_package_with_submodules() -> None:
    review_module = importlib.import_module("app.services.review")

    # Ensure review has been refactored into a package namespace.
    assert hasattr(review_module, "__path__")
    assert hasattr(review_module, "ReviewService")
    assert hasattr(review_module, "ReviewResultParser")
    assert hasattr(review_module, "llm_router")
