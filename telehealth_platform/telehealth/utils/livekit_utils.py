import os
import time
import frappe
from frappe import _

try:
    from livekit import api
except ImportError:
    api = None

def get_livekit_settings():
    """
    Retrieves LiveKit settings from site config or defaults.
    """
    settings = {
        "url": frappe.conf.get("livekit_url") or os.getenv("LIVEKIT_URL") or "wss://livekit.example.com",
        "api_key": frappe.conf.get("livekit_api_key") or os.getenv("LIVEKIT_API_KEY"),
        "api_secret": frappe.conf.get("livekit_api_secret") or os.getenv("LIVEKIT_API_SECRET"),
    }
    return settings

def generate_token(room_name, identity, name=None, metadata=None, is_publisher=True):
    """
    Generates a LiveKit access token.
    """
    settings = get_livekit_settings()
    
    if not settings["api_key"] or not settings["api_secret"]:
        frappe.log_error("LiveKit API Key or Secret not configured", "LiveKit Integration")
        # Critical Fix: Fail fast instead of returning valid-looking dummy token
        raise frappe.exceptions.ConfigError(_("LiveKit API Key or Secret is not configured in site_config.json"))

    if api:
        # Using official SDK if available
        token = api.AccessToken(settings["api_key"], settings["api_secret"]) \
            .with_identity(identity) \
            .with_name(name or identity) \
            .with_metadata(metadata or "") \
            .with_grants(api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=is_publisher,
                can_subscribe=True,
                can_publish_data=True
            ))
        return token.to_jwt()
    else:
        # Fallback to manual JWT if SDK is literal missing
        # This is a simplified version, ideally use the SDK
        try:
            import jwt
            payload = {
                "exp": int(time.time()) + 3600,
                "iss": settings["api_key"],
                "sub": identity,
                "nbf": int(time.time()),
                "video": {
                    "room": room_name,
                    "roomJoin": True,
                    "canPublish": is_publisher,
                    "canSubscribe": True,
                    "canPublishData": True
                },
                "metadata": metadata or "",
                "name": name or identity
            }
            return jwt.encode(payload, settings["api_secret"], algorithm="HS256")
            return jwt.encode(payload, settings["api_secret"], algorithm="HS256")
        except ImportError:
            frappe.log_error("PyJWT not installed for LiveKit fallback", "LiveKit Integration")
            raise frappe.exceptions.ConfigError(_("PyJWT library missing and LiveKit SDK not found"))

def get_server_url():
    settings = get_livekit_settings()
    return settings["url"]

def verify_webhook(token, body):
    """
    Verifies the LiveKit webhook signature.
    Returns decoded event dict if valid, or None/Raises error.
    """
    settings = get_livekit_settings()
    api_key = settings["api_key"]
    api_secret = settings["api_secret"]
    
    if not api_key or not api_secret:
        # If not configured, we can't verify. For MVP we might log warning and allow?
        # But for 'Critical Security compliance' we should fail or return False.
        frappe.log_error("LiveKit API Key/Secret missing for webhook verification", "LiveKit Integration")
        return False

    if api:
        try:
            receiver = api.WebhookReceiver(api_key, api_secret)
            # receive returns the event object
            return receiver.receive(body.decode('utf-8'), token)
        except Exception as e:
            frappe.log_error(f"LiveKit SDK Webhook verification failed: {str(e)}", "LiveKit Integration")
            return None
    else:
        # Manual verification
        try:
            import jwt
            import hashlib
            
            # Decode token
            decoded = jwt.decode(token, api_secret, algorithms=["HS256"])
            
            # Verify body hash
            sha256_hash = hashlib.sha256(body).hexdigest()
            if decoded.get("sha256") != sha256_hash:
                frappe.log_error("Body hash mismatch", "LiveKit Integration")
                return None
                
            return decoded # Return the payload as the event representation (simplified)
            
        except Exception as e:
            frappe.log_error(f"Manual Webhook verification failed: {str(e)}", "LiveKit Integration")
            return None
