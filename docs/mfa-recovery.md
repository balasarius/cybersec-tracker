# MFA enrollment and recovery

Privileged users authenticate with their password and a confirmed TOTP device. A privileged account without a device is restricted to enrollment. Enrollment displays the authenticator configuration URI once and requires a valid current token before confirmation.

Ten single-use recovery codes are generated after confirmation. Only Argon2 hashes are stored; plaintext codes are shown once and must be kept outside the platform. A recovery code completes the second authentication step and is atomically marked used. Repeated second-factor failures discard the five-minute pre-authentication session after five attempts.

Self-service reset is deliberately unavailable. The `reset_mfa` domain operation supports administrator-assisted recovery only when a different, MFA-verified Security administrator supplies a reason and both accounts have active membership in the same organisation. It deletes the target's devices and recovery codes, invalidates every existing target session, and appends an `authentication.mfa_reset` audit event. An administrator UI is deferred until the general privileged-command interface exists; operators must not perform direct database resets.

Changing an active membership or business-unit grant increments the user's authorization version. Middleware compares that version with every authenticated session and logs out stale sessions before serving protected content.
