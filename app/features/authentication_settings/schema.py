from pydantic import BaseModel, model_validator


class AuthenticationSettingsUpdate(BaseModel):
    otp_enabled: bool
    email_otp_enabled: bool
    sms_otp_enabled: bool

    @model_validator(mode="after")
    def validate_delivery_channels(self):
        if self.otp_enabled and not (self.email_otp_enabled or self.sms_otp_enabled):
            raise ValueError("Enable at least one OTP delivery channel")
        return self
