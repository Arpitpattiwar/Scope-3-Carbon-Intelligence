"""
Email Service
=============
Sends transactional emails via SMTP.
If SMTP_USER is empty (dev mode), prints to console instead.

Gmail setup:
  1. Enable 2-factor auth on your Google account
  2. Go to https://myaccount.google.com/apppasswords
  3. Create an app password for "Mail"
  4. Set SMTP_USER=your@gmail.com and SMTP_PASSWORD=the-16-char-app-password
     in docker-compose.yml
"""
from typing import Optional
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

logger = logging.getLogger(__name__)


def _region_label(region: str) -> str:
    """Convert enum string like 'Region.north' or 'north' → 'North'."""
    # Handle both raw string "north" and enum repr "Region.north"
    val = region.split(".")[-1] if "." in region else region
    return val.title()


def send_email(to: str, subject: str, body: str, html: Optional[str] = None) -> bool:
    if not settings.SMTP_USER:
        print("\n" + "=" * 60)
        print("[EMAIL — not sent, SMTP not configured]")
        print(f"To:      {to}")
        print(f"Subject: {subject}")
        print("-" * 60)
        print(body)
        print("=" * 60 + "\n")
        return True

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = settings.SMTP_USER
    msg["To"]      = to
    msg.attach(MIMEText(body, "plain"))
    if html:
        msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_USER, to, msg.as_string())
        logger.info(f"Email sent to {to} — {subject}")
        return True
    except Exception as e:
        logger.error(f"Email send failed to {to}: {e}")
        return False


def send_vendor_invitation(
    email: str,
    temp_password: str,
    invited_by_name: str,
    region: str,
) -> bool:
    region_display = _region_label(region)
    login_url = f"{settings.FRONTEND_URL}/login"

    subject = "Invitation to Scope 3 Emissions Platform"

    body = f"""Dear Vendor Partner,

You have been invited by {invited_by_name} to submit emissions data on the
Scope 3 Emissions Platform.

Login URL:          {login_url}
Email:              {email}
Temporary Password: {temp_password}

This password expires in 48 hours.
You will be prompted to set a new password and complete your company
profile on first login.

Assigned Region: {region_display}

If you did not expect this invitation, please ignore this email.

Regards,
ESG Platform
"""

    html = f"""
<div style="font-family:Arial,sans-serif;max-width:520px;margin:0 auto;padding:32px 0">
  <div style="background:#0f8660;padding:20px 28px;border-radius:12px 12px 0 0">
    <h2 style="color:#fff;margin:0;font-size:20px">Scope 3 Emissions Platform</h2>
  </div>
  <div style="background:#f8faf9;padding:28px;border:1px solid #e4ede9;border-radius:0 0 12px 12px">
    <p style="color:#374151;margin-top:0">Dear Vendor Partner,</p>
    <p style="color:#374151">You have been invited by <strong>{invited_by_name}</strong>
    to submit emissions data on the Scope 3 Emissions Platform.</p>

    <div style="background:#fff;border:1px solid #e4ede9;border-radius:8px;padding:16px 20px;margin:20px 0">
      <table style="border-collapse:collapse;width:100%">
        <tr>
          <td style="color:#6b7280;font-size:13px;padding:5px 0;width:40%">Login URL</td>
          <td style="font-size:13px;font-weight:600;padding:5px 0">
            <a href="{login_url}" style="color:#0f8660">{login_url}</a>
          </td>
        </tr>
        <tr>
          <td style="color:#6b7280;font-size:13px;padding:5px 0">Email</td>
          <td style="color:#111827;font-size:13px;font-weight:600;padding:5px 0">{email}</td>
        </tr>
        <tr>
          <td style="color:#6b7280;font-size:13px;padding:5px 0">Temp Password</td>
          <td style="color:#111827;font-size:13px;font-weight:700;font-family:monospace;padding:5px 0;letter-spacing:1px">{temp_password}</td>
        </tr>
        <tr>
          <td style="color:#6b7280;font-size:13px;padding:5px 0">Region</td>
          <td style="color:#111827;font-size:13px;font-weight:600;padding:5px 0">{region_display}</td>
        </tr>
      </table>
    </div>

    <p style="color:#6b7280;font-size:13px">
      This password expires in <strong>48 hours</strong>.
      You will be prompted to set a new password and complete your profile on first login.
    </p>
    <p style="color:#6b7280;font-size:13px;margin-bottom:0">
      If you did not expect this invitation, please ignore this email.
    </p>
  </div>
</div>
"""
    return send_email(to=email, subject=subject, body=body, html=html)


def send_record_status_email(
    to: str,
    vendor_name: str,
    record_id: int,
    status: str,
    reason: Optional[str] = None,
) -> bool:
    if status == "approved":
        subject = f"Emission Record #{record_id} Approved"
        body = f"""Dear {vendor_name},

Your emission record (ID: #{record_id}) has been approved.

View your records at: {settings.FRONTEND_URL}/emissions

Regards,
ESG Platform
"""
    else:
        subject = f"Emission Record #{record_id} Rejected"
        body = f"""Dear {vendor_name},

Your emission record (ID: #{record_id}) has been rejected.

Reason: {reason or 'No reason provided.'}

Please correct the data and resubmit at: {settings.FRONTEND_URL}/submit

Regards,
ESG Platform
"""
    return send_email(to=to, subject=subject, body=body)


def send_weekly_digest(
    to: str,
    name: str,
    total_co2e: float,
    record_count: int,
    pending_count: int,
    region: str,
) -> bool:
    region_display = _region_label(region)
    subject = f"Scope 3 Weekly Digest — {region_display} Region"
    body = f"""Hi {name},

Here is your weekly Scope 3 summary for {region_display}:

  Total Emissions:    {total_co2e:.2f} tCO2e
  Records Submitted:  {record_count}
  Pending Approval:   {pending_count}

View full dashboard: {settings.FRONTEND_URL}/dashboard

Regards,
ESG Platform
"""
    return send_email(to=to, subject=subject, body=body)
