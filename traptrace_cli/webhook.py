"""
Trap Alert Webhook Exporter for TrapTrace CLI.
Sends real-time error alerts, transaction panics, and diagnostic incident reports to Discord/Slack webhooks.
"""

import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

class WebhookNotifier:
    """Dispatches formatted trap alerts to webhook endpoints."""

    def __init__(self, webhook_url: str):
        self.url = webhook_url

    def send_trap_alert(self, title: str, details: Dict[str, Any], is_test: bool = False) -> bool:
        """Send a formatted JSON webhook notification."""
        payload = {
            "username": "TrapTrace Monitor",
            "content": f"🚨 **Soroban Host Trap Detected** ({details.get('network', 'testnet')})",
            "embeds": [
                {
                    "title": f"⚡ {title}",
                    "description": details.get("summary", "Contract panic or diagnostic trap caught on-chain."),
                    "color": 15158332 if not is_test else 3123596,  # Red for trap, Teal for test
                    "fields": [
                        {"name": "Contract ID", "value": f"`{details.get('contract_id', 'N/A')}`", "inline": True},
                        {"name": "Error Code", "value": f"`{details.get('error_code', 'UNKNOWN')}`", "inline": True},
                        {"name": "Status", "value": "TEST ALERT" if is_test else "CRITICAL", "inline": True}
                    ],
                    "footer": {"text": "TrapTrace Real-Time Diagnostics"}
                }
            ]
        }

        try:
            req = urllib.request.Request(
                self.url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "User-Agent": "TrapTrace-Webhook/0.3.0"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status in (200, 204)
        except Exception:
            return False
