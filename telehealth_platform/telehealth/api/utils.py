import datetime
import jwt
import frappe
from frappe import _

# JWT Configuration
# In production, these should be in site_config.json
JWT_SECRET = frappe.local.conf.get("jwt_secret") or frappe.get_conf().get("encryption_key")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRY = 3600  # 1 hour per TDD
REFRESH_TOKEN_EXPIRY = 604800  # 7 days per TDD

def generate_tokens(user_id):
    """
    Generates access and refresh tokens for a user.
    """
    now = datetime.datetime.utcnow()
    
    # Access Token
    access_payload = {
        "exp": now + datetime.timedelta(seconds=ACCESS_TOKEN_EXPIRY),
        "iat": now,
        "sub": user_id,
        "type": "access"
    }
    access_token = jwt.encode(access_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    # Refresh Token
    refresh_payload = {
        "exp": now + datetime.timedelta(seconds=REFRESH_TOKEN_EXPIRY),
        "iat": now,
        "sub": user_id,
        "type": "refresh"
    }
    refresh_token = jwt.encode(refresh_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    return access_token, refresh_token

def verify_token(token, token_type="access"):
    """
    Verifies a JWT token.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != token_type:
            return None
        return payload
    except jwt.ExpiredSignatureError:
        frappe.throw(_("Token has expired"), frappe.AuthenticationError)
    except jwt.InvalidTokenError:
        frappe.throw(_("Invalid token"), frappe.AuthenticationError)
    except Exception:
        frappe.throw(_("Authentication failed"), frappe.AuthenticationError)

def get_user_role(user):
    """
    Maps Frappe roles to contract roles (Patient, Doctor, Admin).
    """
    roles = frappe.get_roles(user)
    if "System Manager" in roles or "Administrator" in roles:
        return "Admin"
    if "Healthcare Practitioner" in roles:
        return "Doctor"
    if "Patient" in roles:
        return "Patient"
    return "Patient" # Default
