"""Email service for sending verification codes."""
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import config


class EmailService:
    """Service for sending emails."""

    @staticmethod
    async def send_verification_code(email: str, code: str) -> bool:
        """Send verification code to email."""
        try:
            # إعداد الرسالة
            message = MIMEMultipart("alternative")
            message["Subject"] = "DTC Job Bot - Verification Code"
            message["From"] = config.EMAIL_FROM
            message["To"] = email

            text = f"""
Your verification code is: {code}

This code will expire in {config.VERIFICATION_CODE_EXPIRY_MINUTES} minutes.

If you didn't request this code, please ignore this email.
            """

            html = f"""
<html>
  <body>
    <h2>DTC Job Bot - Verification Code</h2>
    <p>Your verification code is: <strong>{code}</strong></p>
    <p>This code will expire in {config.VERIFICATION_CODE_EXPIRY_MINUTES} minutes.</p>
    <p>If you didn't request this code, please ignore this email.</p>
  </body>
</html>
            """

            part1 = MIMEText(text, "plain")
            part2 = MIMEText(html, "html")

            message.attach(part1)
            message.attach(part2)

            # اختيار طريقة الاتصال حسب المنفذ
            if config.SMTP_PORT == 465:
                # SSL مباشر
                await aiosmtplib.send(
                    message,
                    hostname=config.SMTP_HOST,
                    port=config.SMTP_PORT,
                    username=config.SMTP_USER,
                    password=config.SMTP_PASSWORD,
                    use_tls=True
                )
            else:
                # STARTTLS (عادة المنفذ 587)
                await aiosmtplib.send(
                    message,
                    hostname=config.SMTP_HOST,
                    port=config.SMTP_PORT,
                    username=config.SMTP_USER,
                    password=config.SMTP_PASSWORD,
                    start_tls=True
                )

            return True
        except Exception as e:
            print(f"Error sending email: {e}")
            return False