# MFA enrollment and recovery

Privileged users authenticate with their password and a confirmed TOTP device. A privileged account without a device is restricted to enrollment. Enrollment displays the authenticator configuration URI once and requires a valid current token before confirmation.

Ten single-use recovery codes are generated after confirmation. Only Argon2 hashes are stored; plaintext codes are shown once and must be kept outside the platform. A recovery code completes the second authentication step and is atomically marked used. Repeated second-factor failures discard the five-minute pre-authentication session after five attempts.

Self-service reset and administrator-assisted recovery are deliberately unavailable in the current slice. Until the audited administrator workflow is implemented, loss of every device and recovery code requires a database administrator following an approved operational procedure. This is not acceptable for production release and remains an explicit Stage 2 gate item.

Changing an active membership or business-unit grant increments the user's authorization version. Middleware compares that version with every authenticated session and logs out stale sessions before serving protected content.
