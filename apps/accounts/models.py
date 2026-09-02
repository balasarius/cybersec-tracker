# SPDX-License-Identifier: Apache-2.0
"""Stable local identities and future external identity links."""

import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Internal identity whose primary key survives identity-provider changes."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(blank=False)


class ExternalIdentity(models.Model):
    """A provider subject linked to, but never replacing, an internal user."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="external_identities")
    provider = models.CharField(max_length=100)
    subject = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("provider", "subject"), name="accounts_external_identity_unique"
            )
        ]
