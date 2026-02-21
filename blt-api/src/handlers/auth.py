
import hashlib
import secrets
from typing import Any, Dict, Optional

from libs.db import get_db_safe
from utils import parse_json_body, error_response, cors_headers, check_required_fields, json_response, convert_single_d1_result, extract_id_from_result



async def handle_signup(
    request: Any,
    env: Any,
    path_params: Dict[str, str],
    query_params: Dict[str, str],
    path: str
) -> Any:
    """Handle user signup/registration."""

    method = str(request.method).upper()
    if method != "POST":
        return error_response( "Method Not Allowed", 404)
    try: 
        body = await parse_json_body(request)
        if not body:
            return error_response("Invalid JSON body", 400)

        required_fields = ["username", "password", "email"]

        valid, missing_field = await check_required_fields(body, required_fields)

        if not valid:
            return error_response("Missing required field",400)
        
        
        # getting db connection
        try :
            db = await get_db_safe(env)
        except Exception as e:       
            return error_response("Database connection error", 500)

        # Check if username or email already exists
        stmt = await db.prepare("SELECT id FROM users WHERE username = ? OR email = ?").bind(body["username"], body["email"]).first()
        
        existing_user = None
        if stmt:
            existing_user = stmt.to_py() if hasattr(stmt, 'to_py') else dict(stmt)

        if existing_user:
            return error_response("User already exists", 400)

        # Hash the password using PBKDF2
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac('sha256', body["password"].encode('utf-8'), salt.encode('utf-8'), 100000)
        hashed_password = f"{salt}${password_hash.hex()}"

        # Insert the new user into the database
        result = await db.prepare("INSERT INTO users (username, email, password) VALUES (?, ?, ?)").bind(body["username"], body["email"], hashed_password).run()
        
        # Get the last inserted ID
        last_id_result = await db.prepare('SELECT last_insert_rowid() as id').first()
        user_id = extract_id_from_result(last_id_result, 'id')
        
        return json_response({"message": "User registered successfully", "user_id": user_id}, status=201, headers=cors_headers())

    except Exception as e:
        print("Error during signup:", str(e))
        return error_response("Internal Server Error", 500)