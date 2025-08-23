#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ğŸ“§ GEM OS - Email Plugin (plugins/email_plugin.py)

Provides email management via SMTP/IMAP.
Registers commands with PluginManager:
- "email:send"
- "email:list"
"""

from __future__ import annotations
import smtplib
import imaplib
import email
import json
import os
from email.mime.text import MIMEText
from typing import List, Dict

CONFIG_FILE = "data/email_config.json"


def _load_config() -> Dict:
    """Load email configuration (SMTP/IMAP)."""
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def send_email(to_addr: str, subject: str, body: str) -> str:
    """Send an email using SMTP."""
    cfg = _load_config()
    if not cfg:
        return "âš ï¸� Email config not found. Please create data/email_config.json"
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["From"] = cfg["user"]
        msg["To"] = to_addr
        msg["Subject"] = subject

        with smtplib.SMTP(cfg["smtp_host"], cfg.get("smtp_port", 587)) as server:
            server.starttls()
            server.login(cfg["user"], cfg["password"])
            server.send_message(msg)

        return f"âœ… Email sent to {to_addr} with subject '{subject}'"
    except Exception as e:
        return f"â�Œ Error sending email: {e}"


def list_emails(limit: int = 5) -> str:
    """List recent emails via IMAP."""
    cfg = _load_config()
    if not cfg:
        return "âš ï¸� Email config not found. Please create data/email_config.json"
    try:
        with imaplib.IMAP4_SSL(cfg["imap_host"], cfg.get("imap_port", 993)) as imap:
            imap.login(cfg["user"], cfg["password"])
            imap.select("inbox")
            status, data = imap.search(None, "ALL")
            if status != "OK":
                return "â�Œ Error fetching emails."

            email_ids = data[0].split()[-limit:]
            messages = []
            for eid in reversed(email_ids):
                status, msg_data = imap.fetch(eid, "(RFC822)")
                if status != "OK":
                    continue
                msg = email.message_from_bytes(msg_data[0][1])
                messages.append(f"ğŸ“§ {msg['From']} â†’ {msg['Subject']}")

            return "ğŸ“¬ Recent Emails:\n" + "\n".join(messages)
    except Exception as e:
        return f"â�Œ Error listing emails: {e}"


def register(plugin_manager):
    """Register plugin commands."""
    plugin_manager.register_command("email:send", send_email)
    plugin_manager.register_command("email:list", list_emails)
