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
    async def authenticate_user(code: str, redirect_uri: str, db) -> Tuple[Dict, bool]:
        """Authenticate user with Google OAuth"""
        try:
            # Verify the token with Google
            user_info = await GoogleOAuth.verify_token(code)
            
            # Check if user exists
            with get_db() as conn:
                user = execute_query_single(
                    conn,
                    """
                    SELECT * FROM users 
                    WHERE google_id = %s OR email = %s
                    """,
                    (user_info['sub'], user_info['email'])
                )
                
                if not user:
                    # Create new user
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
                
                # Update existing user if needed
                if not user['google_id']:
                    execute_query_single(
                        conn,
                        """
                        UPDATE users 
                        SET google_id = %s, is_anonymous = false
                        WHERE id = %s
                        RETURNING *
                        """,
                        (user_info['sub'], user['id'])
                    )
                    conn.commit()
                
                return user, False
                
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
