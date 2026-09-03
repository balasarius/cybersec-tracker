# SPDX-License-Identifier: Apache-2.0
"""Audit append, correlation, immutability, and integrity tests."""

import uuid

import pytest
from django.db import DatabaseError, connection, transaction
from django.test import Client

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.audit.services import append_event, record_privileged_read, redact, verify_chain
from apps.tenancy.models import Organisation

pytestmark = pytest.mark.django_db(transaction=True)


def test_append_event_builds_verifiable_chain() -> None:
    organisation = Organisation.objects.create(name="Audit Org", slug="audit-org")
    first = append_event(
        organisation=organisation,
        action="organisation.created",
        object_type="organisation",
        object_id=str(organisation.id),
        actor=None,
        actor_label="system",
    )
    second = append_event(
        organisation=organisation,
        action="organisation.reviewed",
        object_type="organisation",
        object_id=str(organisation.id),
        actor=None,
        actor_label="system",
        reason="test",
    )

    assert first.sequence == 1
    assert second.sequence == 2
    assert second.previous_hash == first.event_hash
    assert verify_chain(organisation=organisation).valid is True


def test_append_event_redacts_nested_secrets() -> None:
    organisation = Organisation.objects.create(name="Redaction Org", slug="redaction-org")

    event = append_event(
        organisation=organisation,
        action="credential.tested",
        object_type="source_account",
        object_id="one",
        actor=None,
        actor_label="system",
        data={"token": "do-not-store", "nested": {"password": "also-secret", "result": "ok"}},
    )

    assert event.data == {
        "token": "[REDACTED]",
        "nested": {"password": "[REDACTED]", "result": "ok"},
    }
    assert verify_chain(organisation=organisation).valid is True


def test_redaction_handles_lists_and_scalar_values() -> None:
    assert redact([{"token": "secret"}, "safe"]) == [{"token": "[REDACTED]"}, "safe"]
    assert redact(7) == 7


def test_append_event_requires_one_consistent_organisation_identifier() -> None:
    first = Organisation.objects.create(name="First audit org", slug="first-audit-org")
    second = Organisation.objects.create(name="Second audit org", slug="second-audit-org")
    common = {
        "action": "test",
        "object_type": "test",
        "object_id": "one",
        "actor": None,
        "actor_label": "system",
    }

    with pytest.raises(ValueError, match="required"):
        append_event(**common)
    with pytest.raises(ValueError, match="do not match"):
        append_event(organisation=first, organisation_id=second.id, **common)


def test_model_and_queryset_reject_mutation() -> None:
    organisation = Organisation.objects.create(name="Immutable Org", slug="immutable-org")
    event = append_event(
        organisation=organisation,
        action="test.created",
        object_type="test",
        object_id="one",
        actor=None,
        actor_label="system",
    )

    event.reason = "changed"
    with pytest.raises(TypeError, match="append-only"):
        event.save()
    with pytest.raises(TypeError, match="append-only"):
        event.delete()
    with pytest.raises(TypeError, match="append-only"):
        AuditEvent.objects.filter(pk=event.pk).update(reason="changed")
    with pytest.raises(TypeError, match="append-only"):
        AuditEvent.objects.filter(pk=event.pk).delete()


def test_database_trigger_rejects_direct_mutation() -> None:
    organisation = Organisation.objects.create(name="Trigger Org", slug="trigger-org")
    event = append_event(
        organisation=organisation,
        action="test.created",
        object_type="test",
        object_id="one",
        actor=None,
        actor_label="system",
    )

    with pytest.raises(DatabaseError, match="append-only"), transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE audit_auditevent SET reason = %s WHERE id = %s",
                ["tampered", event.id],
            )


def test_correlation_middleware_accepts_valid_uuid(client: Client) -> None:
    correlation = uuid.uuid4()

    response = client.get("/health/live", headers={"X-Correlation-ID": str(correlation)})

    assert response.headers["X-Correlation-ID"] == str(correlation)


def test_correlation_middleware_replaces_invalid_value(client: Client) -> None:
    response = client.get("/health/live", headers={"X-Correlation-ID": "not-a-uuid"})

    assert uuid.UUID(response.headers["X-Correlation-ID"])


def test_privileged_read_requires_purpose_and_is_audited() -> None:
    organisation = Organisation.objects.create(name="Read Org", slug="read-org")
    actor = User.objects.create_user(username="reader")

    with pytest.raises(ValueError, match="purpose"):
        record_privileged_read(
            organisation=organisation,
            actor=actor,
            object_type="evidence",
            object_id="one",
            purpose=" ",
        )
    event = record_privileged_read(
        organisation=organisation,
        actor=actor,
        object_type="evidence",
        object_id="one",
        purpose="Investigating remediation",
        export=True,
    )

    assert event.action == "privileged.export"
    assert event.reason == "Investigating remediation"
    assert event.actor == actor
