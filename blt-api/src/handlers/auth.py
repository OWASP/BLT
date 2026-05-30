
import hashlib
import hmac
import json
import re
import secrets
import time
from typing import Any, Dict
from urllib.parse import urlparse

from libs.db import get_db_safe
from utils import parse_json_body, error_response, cors_headers, check_required_fields, get_blt_api_url
from libs.constant import __HASHING_ITERATIONS
from libs.jwt_utils import create_access_token, decode_jwt
from libs.data_protection import encrypt_sensitive, decrypt_sensitive, blind_index
from services.email_service import EmailService
from workers import Response
from models import User, UserApiKey, UserAuthIdentity
from libs.rate_limit import get_client_ip, is_rate_limited
from libs.api_key import generate_user_api_key, hash_user_api_key, user_api_key_prefix
from libs.auth_context import get_authenticated_user_id

import logging

_USERNAME_RE = re.compile(r'^[a-zA-Z0-9_.-]{3,30}$')
_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')

SIGNUP_RATE_LIMIT: Dict[str, list] = {}
SIGNIN_RATE_LIMIT: Dict[str, list] = {}
_RATE_LIMIT_WINDOW_SECONDS = 60
_SIGNUP_MAX_REQUESTS = 5
_SIGNIN_MAX_REQUESTS = 10
ACCESS_TOKEN_EXPIRES_SECONDS = 24 * 3600
EMAIL_VERIFICATION_EXPIRES_SECONDS = 24 * 3600
EMAIL_VERIFICATION_PURPOSE = "email_verification"
LOCAL_AUTH_OTP_DEFAULT = "000000"


def _utc_timestamp() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())


def _env_text(env: Any, name: str) -> str:
    return str(getattr(env, name, "") or "").strip()


def _sendgrid_config(env: Any) -> Dict[str, str] | None:
    api_key = _env_text(env, "SENDGRID_API_KEY") or _env_text(env, "SENDGRID_PASSWORD")
    from_email = _env_text(env, "FROM_EMAIL")
    if not api_key or not from_email:
        return None

    return {
        "smtp_username": _env_text(env, "SENDGRID_USERNAME") or "apikey",
        "smtp_password": api_key,
        "from_email": from_email,
    }


def _local_auth_otp(env: Any) -> str:
    return _env_text(env, "LOCAL_AUTH_OTP") or LOCAL_AUTH_OTP_DEFAULT


def _is_local_request(request: Any) -> bool:
    url = str(getattr(request, "url", "") or "")
    if not url:
        return False

    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    return hostname in {"localhost", "127.0.0.1", "::1"}


def generate_jwt_token(user_id: int, secret: str, expires_in: int = 3600) -> str:
    """
    Generate a purpose-scoped JWT email verification token for a user.
    
    Creates a signed JWT token containing the user ID, verification purpose,
    and expiration time.
    
    Args:
        user_id: The database ID of the user
        secret: JWT secret key for signing the token (from env.JWT_SECRET)
        expires_in: Token validity duration in seconds (default: 1 hour)
    
    Returns:
        Signed JWT token string that can be used in verification links
    """
    payload = {
        "user_id": user_id,
        "purpose": EMAIL_VERIFICATION_PURPOSE,
        "exp": int(time.time()) + expires_in,
    }
    token = create_access_token(payload, secret, expires_in=expires_in)
    return token

async def handle_signup(
    request: Any,
    env: Any,
    path_params: Dict[str, str],
    query_params: Dict[str, str],
    path: str
) -> Any:
    """
    Handle user registration/signup endpoint (POST /auth/signup).
    
    Creates a new user account with hashed password (PBKDF2-SHA256),
    sends verification email via SendGrid, and returns success response.
    
    Required fields in request body:
        - username: Unique username for the account
        - email: User email address (must be unique)
        - password: Plain text password (will be hashed with salt)
    
    Process:
        1. Validates request method and required fields
        2. Checks for existing username/email
        3. Hashes password with random salt using PBKDF2
        4. Inserts user into database with is_active=false
        5. Generates verification JWT token (24 hour expiry)
        6. Sends verification email with token link
    
    Returns:
        201 Created with message to check email for verification link,
        or 400/500 error if validation fails or user exists
    """
    base_url = get_blt_api_url(env)
    method = str(request.method).upper()
    logger = logging.getLogger(__name__)
    if method != "POST":
        return error_response( "Method Not Allowed", 405, headers={"Allow": "POST"})
    try: 
        client_ip = get_client_ip(request)
        if is_rate_limited(client_ip, SIGNUP_RATE_LIMIT, _RATE_LIMIT_WINDOW_SECONDS, _SIGNUP_MAX_REQUESTS):
            return error_response("Too many requests. Please try again later.", status=429)

        body = await parse_json_body(request)
        if not body:
            return error_response("Invalid JSON body", 400)

        required_fields = ["username", "password", "email"]

        valid, missing_field = await check_required_fields(body, required_fields)

        if not valid:
            return error_response("Missing required field",400)
        
        username_val = body.get("username")
        email_val = body.get("email")
        redirect_uri_val = body.get("redirect_uri", "")

        if not isinstance(username_val, str) or not isinstance(email_val, str) or not isinstance(redirect_uri_val, str):
            return error_response("Username, email, and redirect_uri must be strings", 400)

        username = username_val.strip()
        email = email_val.strip().lower()
        redirect_uri = redirect_uri_val.strip()

        # --- Input Validation ---
        password = body["password"]
        if not isinstance(password, str) or not (12 <= len(password) <= 128 and
                re.search(r'[A-Z]', password) and
                re.search(r'[a-z]', password) and
                re.search(r'\d', password) and
                re.search(r'[^a-zA-Z0-9]', password)):
            return error_response(
                "Password must be a string of 12-128 characters and contain at least one uppercase letter, one lowercase letter, one number, and one special character",
                400,
            )

        if len(email) > 254:
            return error_response("Email too long", 400)

        if not _EMAIL_RE.match(email):
            return error_response("Invalid email format", 400)

        if not _USERNAME_RE.match(username):
            return error_response(
                "Username must be 3-30 characters and may include letters, numbers, underscores, dots, and hyphens",
                400,
            )
        # --- End Input Validation ---

        # Validate redirect_uri against whitelist if provided
        if redirect_uri:
            allowed_uris = [u.strip() for u in getattr(env, "ALLOWED_REDIRECT_URIS", "").split(",") if u.strip()]
            if not any(redirect_uri.startswith(allowed) for allowed in allowed_uris):
                return error_response("Invalid redirect_uri", 400)

        is_local_signup = _is_local_request(request)
        dev_otp = str(body.get("dev_otp", "") or "").strip()
        if is_local_signup:
            if dev_otp:
                return error_response("Local verification code must be submitted after account creation", 400)
            email_config = None
        else:
            if dev_otp:
                return error_response("Local verification code is only available in local development", 400)

            email_config = _sendgrid_config(env)
            if email_config is None:
                return error_response(
                    "Email service is not configured. Set SENDGRID_API_KEY and FROM_EMAIL before signing up users.",
                    503,
                    headers=cors_headers(),
                )

        # getting db connection
        try:
            db = await get_db_safe(env)
        except Exception as e:
            return error_response("Database connection error", 500)

        email_hash = blind_index(email, env, "users.email")
        username_hash = blind_index(username, env, "users.username")

        # Check if username or email already exists using blind indexes
        existing_user = await User.objects(db).filter(username_hash=username_hash).first()
        if not existing_user:
            existing_user = await User.objects(db).filter(email_hash=email_hash).first()

        if existing_user:
            return error_response("User already exists", 400)

        # Hash the password using PBKDF2
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac('sha256', body["password"].encode('utf-8'), salt.encode('utf-8'), __HASHING_ITERATIONS)
        hashed_password = f"{salt}${password_hash.hex()}"

        # Insert encrypted sensitive fields only.
        user_data = {
            "username_encrypted": encrypt_sensitive(username, env),
            "username_hash": username_hash,
            "email_encrypted": encrypt_sensitive(email, env),
            "email_hash": email_hash,
            "password": hashed_password,
            "is_active": False,
        }

        try:
            new_user = await User.create(db, **user_data)
        except Exception as e:
            if "email_encrypted" in str(e) or "email_hash" in str(e) or "username_encrypted" in str(e):
                return error_response(
                    "Encrypted user schema not ready. Run migrations to add encrypted user columns.",
                    503,
                )
            raise
        user_id = new_user.get("id") if new_user else None
        if user_id is None:
            return error_response("Failed to create user", 500)

        try:
            await UserAuthIdentity.create(
                db,
                user_id=user_id,
                provider="local",
                provider_user_id=str(user_id),
                provider_username_encrypted=encrypt_sensitive(username, env),
                provider_email_encrypted=encrypt_sensitive(email, env),
                provider_email_hash=email_hash,
            )
        except Exception as e:
            logger.error("Failed to create local auth identity for user %s: %s", user_id, str(e))
            try:
                await User.objects(db).filter(id=user_id).delete()
            except Exception as del_exc:
                logger.error("Failed to roll back user %s after identity failure: %s", user_id, str(del_exc))
            return error_response(
                "Account identity schema not ready. Run migrations to add auth identity columns.",
                503,
                headers=cors_headers(),
            )

        if is_local_signup:
            resp_body = {
                "message": "Account created. Enter the local verification code to activate it.",
                "user_id": user_id,
                "email_verified": False,
                "requires_local_verification": True,
            }
            if redirect_uri:
                resp_body["redirect_to"] = redirect_uri
            return Response.json(resp_body, status=201, headers=cors_headers())

        # Send verification email using SendGrid Web API.
        email_service = EmailService(
            **email_config,
            from_name="OWASP BLT"
        )
        token = generate_jwt_token(user_id, env.JWT_SECRET, expires_in=EMAIL_VERIFICATION_EXPIRES_SECONDS)

        try:
            email_status, email_response = await email_service.send_verification_email(
                to_email=email,
                username=username,
                verification_token=token,
                base_url=base_url,
                expires_hours=EMAIL_VERIFICATION_EXPIRES_SECONDS // 3600,
            )
        except Exception as e:
            logger.error("Exception sending verification email to user %s: %s", user_id, str(e))
            email_status, email_response = 500, str(e)

        if email_status >= 400:
            logger.error("Failed to send verification email to user %s: %s %s", user_id, email_status, email_response)
            # Roll back: delete the newly created user so they can retry
            try:
                await UserAuthIdentity.objects(db).filter(user_id=user_id, provider="local").delete()
                await User.objects(db).filter(id=user_id).delete()
            except Exception as del_exc:
                logger.error("Failed to roll back user %s after email failure: %s", user_id, str(del_exc))
            return error_response(
                "Account created but verification email could not be delivered. Please try again.",
                503,
                headers=cors_headers(),
            )

        resp_body = {
            "message": "User registered successfully, To activate your account, please check your email for the verification link.",
            "user_id": user_id,
        }
        if redirect_uri:
            resp_body["redirect_to"] = redirect_uri
        return Response.json(resp_body, status=201, headers=cors_headers())

    except Exception as e:
        logger.error("Error during signup: %s", str(e))
        return error_response("Internal Server Error", 500)


async def handle_verify_local(
    request: Any,
    env: Any,
    path_params: Dict[str, str],
    query_params: Dict[str, str],
    path: str
) -> Any:
    """Activate a locally-created account using the localhost-only verification code."""
    logger = logging.getLogger(__name__)
    try:
        method = str(request.method).upper()
        if method != "POST":
            return error_response("Method Not Allowed", 405, headers={"Allow": "POST"})

        if not _is_local_request(request):
            return error_response("Local verification is only available in local development", 400)

        body = await parse_json_body(request)
        if not body:
            return error_response("Invalid JSON body", 400)

        identifier_val = body.get("identifier", body.get("username", body.get("email")))
        dev_otp = str(body.get("dev_otp", "") or "").strip()
        if identifier_val is None or not dev_otp:
            return error_response("Missing required field", 400)

        if dev_otp != _local_auth_otp(env):
            return error_response("Invalid local verification code", 400)

        if not isinstance(identifier_val, str):
            return error_response("Username/email must be a string", 400)

        identifier = identifier_val.strip()
        if not identifier:
            return error_response("Missing required field", 400)

        try:
            db = await get_db_safe(env)
        except Exception:
            return error_response("Database connection error", 500)

        if _EMAIL_RE.fullmatch(identifier):
            email_hash = blind_index(identifier.lower(), env, "users.email")
            query = User.objects(db).filter(email_hash=email_hash)
        else:
            if not _USERNAME_RE.fullmatch(identifier):
                return error_response(
                    "Username must be 3-30 characters and may include letters, numbers, underscores, dots, and hyphens",
                    400,
                )
            username_hash = blind_index(identifier, env, "users.username")
            query = User.objects(db).filter(username_hash=username_hash)

        user = await query.first()
        if user is None:
            return error_response("Invalid local verification request", 400)

        if not user.get("is_active"):
            await query.update(
                is_active=True,
                email_verified_at=_utc_timestamp(),
            )

        return Response.json(
            {
                "message": "Local account verified. You can sign in now.",
                "user_id": user["id"],
                "email_verified": True,
            },
            status=200,
            headers=cors_headers(),
        )

    except Exception as e:
        logger.error("Error during local verification: %s", str(e))
        return error_response("Internal Server Error", 500)
    

async def handle_signin(request: Any, env: Any, path_params: Dict[str, str], query_params: Dict[str, str], path: str) -> Any:
    """
    Handle user authentication/login endpoint (POST /auth/signin).
    
    Validates user credentials and returns a JWT token for authenticated API access.
    
    Required fields in request body:
        - identifier: User's username or email address
        - password: Plain text password to verify
    
    Backward compatibility:
        - username: Accepted as a legacy alias for identifier

    Process:
        1. Validates request method and required fields
        2. Fetches user record by username or email blind index
        3. Verifies password using PBKDF2-SHA256 with stored salt
        4. Generates JWT access token (24 hour expiry)
        5. Returns token for use in Authorization header
    
    Returns:
        200 OK with JWT token on successful authentication,
        or 401/400/500 error for invalid credentials or server issues
    """
    logger = logging.getLogger(__name__)
    try:
        jwt_secret = env.JWT_SECRET
        if not jwt_secret:
            return error_response("JWT secret not configured, please configure it using `wrangler secret put JWT_SECRET`", 500)
        method = str(request.method).upper()
        if method != "POST":
            return error_response("Method Not Allowed", 405, headers={"Allow": "POST"})

        client_ip = get_client_ip(request)
        if is_rate_limited(client_ip, SIGNIN_RATE_LIMIT, _RATE_LIMIT_WINDOW_SECONDS, _SIGNIN_MAX_REQUESTS):
            return error_response("Too many requests. Please try again later.", status=429)

        body = await parse_json_body(request)
        if not body:
            return error_response("Invalid JSON body", 400) 
        identifier_val = body.get("identifier", body.get("username", body.get("email")))
        password_val = body.get("password")
        if identifier_val is None or password_val is None:
            return error_response("Missing required field", 400)

        redirect_uri = str(body.get("redirect_uri", "")).strip()
        if redirect_uri:
            allowed_uris = [u.strip() for u in getattr(env, "ALLOWED_REDIRECT_URIS", "").split(",") if u.strip()]
            if not any(redirect_uri.startswith(allowed) for allowed in allowed_uris):
                return error_response("Invalid redirect_uri", 400)

        # getting db connection
        try:
            db = await get_db_safe(env)
        except Exception as e:
            return error_response("Database connection error", 500)

        if not isinstance(identifier_val, str) or not isinstance(password_val, str):
            return error_response("Username/email and password must be strings", 400)

        identifier = identifier_val.strip()
        password = password_val

        if not identifier:
            return error_response("Missing required field", 400)

       # Hardening: password length
        if len(password) < 12:
            return error_response("Password must be at least 12 characters", status=400)

        if not (12 <= len(password) <= 128):
            return error_response("Password must be a string of 12-128 characters", 400)

        if _EMAIL_RE.fullmatch(identifier):
            email_hash = blind_index(identifier.lower(), env, "users.email")
            user = await User.objects(db).filter(email_hash=email_hash).first()
        else:
            if not _USERNAME_RE.fullmatch(identifier):
                return error_response(
                    "Username must be 3-30 characters and may include letters, numbers, underscores, dots, and hyphens",
                    400,
                )
            username_hash = blind_index(identifier, env, "users.username")
            user = await User.objects(db).filter(username_hash=username_hash).first()


        if user is None or "password" not in user:
            return error_response("Invalid username or password", 401)
        stored_password = user["password"]
        
        # Verify the password
        try:
            salt, stored_hash = stored_password.split('$')
        except ValueError:
            return error_response("Invalid username or password", 401)
        password_hash = hashlib.pbkdf2_hmac('sha256', body["password"].encode('utf-8'), salt.encode('utf-8'), __HASHING_ITERATIONS).hex()
        if not hmac.compare_digest(password_hash, stored_hash):
            return error_response("Invalid username or password", 401)

        # Check if account is active (email verified)
        if not user.get("is_active"):
            return error_response(
                "Account not verified. Please check your email for the verification link.",
                403
            )

        # Create JWT token with 24 hour expiration
        token = create_access_token(
            {"user_id": user["id"]}, 
            jwt_secret, 
            expires_in=ACCESS_TOKEN_EXPIRES_SECONDS,
        )

        # Decrypt username for the response
        decrypted_username = (
            decrypt_sensitive(user["username_encrypted"], env)
            if user.get("username_encrypted")
            else user.get("username", "")
        )

        res = {
            "message": "Login successful",
            "access_token": token,
            "token": token,
            "token_type": "Bearer",
            "expires_in": ACCESS_TOKEN_EXPIRES_SECONDS,
            "username": decrypted_username,
        }
        if redirect_uri:
            res["redirect_to"] = redirect_uri
        return Response.json(res, status=200, headers=cors_headers())

    except Exception as e:
        logger.error("Error during login: %s", str(e))
        return error_response("Internal Server Error", 500)


async def handle_verify_email(request: Any, env: Any, path_params: Dict[str, str], query_params: Dict[str, str], path: str) -> Any:
    """
    Handle email verification endpoint (GET /auth/verify-email).
    
    Validates the JWT token from the verification email link and activates the user account.
    This endpoint is accessed via the link sent in the signup verification email.
    
    Required query parameter:
        - token: JWT token containing user_id, purpose, and expiration
    
    Process:
        1. Validates request method is GET
        2. Extracts and decodes JWT token from query params
        3. Verifies token signature and expiration
        4. Activates user account by setting is_active=true
        5. Returns success confirmation
    
    Returns:
        200 OK with success message when email is verified,
        or 400/500 error for invalid/expired tokens or server issues
    """ 
    logger = logging.getLogger(__name__)   
    try:
        db= await  get_db_safe(env)
        jwt_secret = env.JWT_SECRET

        if not jwt_secret:
            return error_response("JWT secret not configured, please configure it using `wrangler secret put JWT_SECRET`", 500)

        method = str(request.method).upper()
        if method != "GET":
            return error_response("Method Not Allowed", 405, headers={"Allow": "GET"})
        
        # Get token from query parameters (e.g., ?token=xxx)
        token = query_params.get("token")
        if not token:
            return error_response("Missing token", 400)
        
        # Verify the token and extract user ID
        payload = decode_jwt(token, jwt_secret)
        if not payload or "user_id" not in payload:
            return error_response("Invalid or expired token", 400)
        if payload.get("purpose") != EMAIL_VERIFICATION_PURPOSE:
            return error_response("Invalid or expired token", 400)
        
        user_id = payload["user_id"]

        # Activate the user's account
        await User.objects(db).filter(id=user_id).update(
            is_active=True,
            email_verified_at=_utc_timestamp(),
        )

        return Response.json({"message": "Email verified successfully, your account is now active."}, status=200, headers=cors_headers())

    except Exception as e:
        
        logger.error("Error during email verification: %s", str(e))
        return error_response("Internal Server Error", 500)


async def handle_api_keys(
    request: Any,
    env: Any,
    path_params: Dict[str, str],
    query_params: Dict[str, str],
    path: str,
) -> Any:
    """Manage user-owned API keys. Requires a Bearer JWT session."""
    logger = logging.getLogger(__name__)
    method = str(request.method).upper()
    if method not in {"GET", "POST", "DELETE"}:
        return error_response("Method Not Allowed", 405, headers={"Allow": "GET, POST, DELETE"})

    user_id = get_authenticated_user_id(request, env)
    if user_id is None:
        return error_response("Authentication required", 401)

    try:
        db = await get_db_safe(env)
    except Exception:
        return error_response("Database connection error", 500)

    try:
        if method == "GET":
            keys = (
                await UserApiKey.objects(db)
                .filter(user_id=user_id, is_active=True)
                .values("id", "name", "key_prefix", "scopes", "is_active", "created", "last_used", "revoked_at")
                .order_by("-created")
                .all()
            )
            return Response.json({"success": True, "data": keys}, status=200, headers=cors_headers())

        if method == "POST":
            body = await parse_json_body(request)
            if not body:
                return error_response("Invalid JSON body", 400)

            name_val = body.get("name")
            if not isinstance(name_val, str):
                return error_response("Missing required field: name", 400)
            name = name_val.strip()
            if not name or len(name) > 80:
                return error_response("API key name must be 1-80 characters", 400)

            scopes_val = body.get("scopes", [])
            if not isinstance(scopes_val, list) or not all(isinstance(scope, str) for scope in scopes_val):
                return error_response("Scopes must be a list of strings", 400)
            scopes = json.dumps(scopes_val, separators=(",", ":"))

            raw_key = generate_user_api_key()
            created_key = await UserApiKey.create(
                db,
                user_id=user_id,
                name=name,
                key_prefix=user_api_key_prefix(raw_key),
                key_hash=hash_user_api_key(raw_key, env),
                scopes=scopes,
                is_active=True,
            )

            data = {
                "id": created_key.get("id") if created_key else None,
                "name": name,
                "key_prefix": user_api_key_prefix(raw_key),
                "api_key": raw_key,
                "scopes": scopes,
                "is_active": True,
                "created": created_key.get("created") if created_key else None,
            }
            return Response.json({"success": True, "data": data}, status=201, headers=cors_headers())

        key_id = path_params.get("id", "")
        if not key_id.isdigit():
            return error_response("Invalid API key ID", 400)

        key_qs = UserApiKey.objects(db).filter(
            id=int(key_id),
            user_id=user_id,
            is_active=True,
        )
        existing_key = await key_qs.first()
        if not existing_key:
            return error_response("API key not found", 404)

        await key_qs.update(
            is_active=False,
            revoked_at=_utc_timestamp(),
        )
        return Response.json({"success": True, "message": "API key revoked"}, status=200, headers=cors_headers())

    except Exception as e:
        logger.error("Error managing API keys for user %s: %s", user_id, str(e))
        return error_response("Internal Server Error", 500)
