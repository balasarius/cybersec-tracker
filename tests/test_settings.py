# SPDX-License-Identifier: Apache-2.0
"""Tests for environment parsing that affects secure deployment behaviour."""

import pytest

from config.settings import env_bool


def test_env_bool_uses_default_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TRACKER_TEST_BOOL", raising=False)

    assert env_bool("TRACKER_TEST_BOOL", default=True) is True


def test_env_bool_accepts_explicit_true_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRACKER_TEST_BOOL", "YeS")

    assert env_bool("TRACKER_TEST_BOOL") is True


def test_env_bool_rejects_other_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRACKER_TEST_BOOL", "not-true")

    assert env_bool("TRACKER_TEST_BOOL", default=True) is False
