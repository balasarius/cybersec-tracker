# SPDX-License-Identifier: Apache-2.0
"""Forms for the two-step local authentication flow."""

from django import forms
from django.contrib.auth.forms import AuthenticationForm


class PasswordLoginForm(AuthenticationForm):
    pass


class TokenForm(forms.Form):
    token = forms.CharField(max_length=128, strip=True, label="Authenticator or recovery code")
