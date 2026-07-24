CREATE TABLE IF NOT EXISTS two_factor_challenges (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    otp_hash VARCHAR NOT NULL,
    delivery_channels VARCHAR NOT NULL,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 5,
    expires_at TIMESTAMPTZ NOT NULL,
    last_sent_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_two_factor_challenges_user_id
    ON two_factor_challenges(user_id);
CREATE INDEX IF NOT EXISTS ix_two_factor_challenges_expires_at
    ON two_factor_challenges(expires_at);
