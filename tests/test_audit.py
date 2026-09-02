# SPDX-License-Identifier: Apache-2.0
"""Audit append, correlation, immutability, and integrity tests."""

import uuid

import pytest
from django.db import DatabaseError, connection, transaction
from django.test import Client

from apps.audit.models import AuditEvent
from apps.audit.services import append_event, verify_chain
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
