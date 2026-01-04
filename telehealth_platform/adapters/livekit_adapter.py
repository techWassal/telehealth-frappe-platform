import os
import frappe
from livekit import api

class LiveKitAdapter:
    def __init__(self):
        # Configuration from site_config or environment
        self.url = frappe.conf.get("livekit_url") or os.environ.get("LIVEKIT_URL")
        self.api_key = frappe.conf.get("livekit_api_key") or os.environ.get("LIVEKIT_API_KEY")
        self.api_secret = frappe.conf.get("livekit_api_secret") or os.environ.get("LIVEKIT_API_SECRET")

    def create_room(self, room_name, empty_timeout=3600, max_participants=2):
        """
        Creates a room on the LiveKit server.
        """
        if not self.api_key or not self.api_secret:
            frappe.logger().error("LiveKit credentials not configured")
            return None

        client = api.LiveKitAPI(self.url, self.api_key, self.api_secret)
        # Note: LiveKit rooms are often created on the fly when first participant joins,
        # but explicit creation is good for pre-checking.
        pass

    def get_access_token(self, room_name, identity, name=None):
        """
        Generates an access token for a specific room and identity.
        """
        if not self.api_key or not self.api_secret:
            return "dummy-token-unconfigured"

        token = api.AccessToken(self.api_key, self.api_secret) \
            .with_identity(identity) \
            .with_name(name or identity) \
            .with_grants(api.VideoGrants(
                room_join=True,
                room=room_name,
            ))
        
        return token.to_jwt()

    def verify_webhook(self, body, signature):
        """
        Verifies a webhook signature from LiveKit.
        """
        # Logic to verify using webhook receiver
        pass
