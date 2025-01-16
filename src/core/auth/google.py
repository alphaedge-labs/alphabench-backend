from google.oauth2 import id_token
from google.auth.transport import requests
from fastapi import HTTPException, status
from typing import Tuple, Dict

from src.config.settings import settings
from src.db.base import get_db, execute_query_single

class GoogleOAuth:
    @staticmethod
    async def verify_token(token: str) -> Dict:
        """Verify Google OAuth token"""
        try:
            idinfo = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                settings.GOOGLE_CLIENT_ID
            )
            
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Wrong issuer.')
                
            return idinfo
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )

    @staticmethod
    async def authenticate_user(code: str, current_user_id: str, redirect_uri: str, db) -> Tuple[Dict, bool]:
        """Authenticate user with Google OAuth"""
        try:
            # Verify the token with Google
            user_info = await GoogleOAuth.verify_token(code)
            
            # Check if user exists by google_id or email first
            with get_db() as conn:
                # First try to find an existing Google user
                user = execute_query_single(
                    conn,
                    """
                    SELECT * FROM users 
                    WHERE google_id = %s OR email = %s
                    """,
                    (user_info['sub'], user_info['email'])
                )
                
                if not user:
                    # Try to find anonymous user from the current session
                    user = execute_query_single(
                        conn,
                        """
                        SELECT * FROM users 
                        WHERE id = %s AND is_anonymous = true
                        """,
                        (current_user_id,)  # We need to get this from the request context
                    )
                    
                    if user:
                        # Update anonymous user with Google info
                        user = execute_query_single(
                            conn,
                            """
                            UPDATE users 
                            SET google_id = %s,
                                email = %s,
                                is_anonymous = false
                            WHERE id = %s
                            RETURNING *
                            """,
                            (user_info['sub'], user_info['email'], user['id'])
                        )
                        conn.commit()
                        return user, False
                    
                    # If no existing user found at all, create new one
                    user = execute_query_single(
                        conn,
                        """
                        INSERT INTO users (email, google_id, is_anonymous)
                        VALUES (%s, %s, false)
                        RETURNING *
                        """,
                        (user_info['email'], user_info['sub'])
                    )
                    conn.commit()
                    return user, True
                
                return user, False
                
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
