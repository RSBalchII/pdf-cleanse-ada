#!/usr/bin/env python3
"""
Adobe OAuth 2.0 Server for Browser-Based Authentication

Allows non-developer users to sign in with their Adobe ID in the browser
and use the PDF Services API without needing developer credentials.

Flow:
  1. User clicks "Sign in with Adobe" → redirected to Adobe OAuth
  2. User authorizes → redirected back with authorization code
  3. Server exchanges code for access token
  4. Token stored in session → API calls use user's token

Requires registering an Adobe OAuth app at:
  https://developer.adobe.com/console → Create project → Add Adobe ID
"""

import os
import sys
import json
import time
import secrets
import urllib.parse
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Optional

import requests

# ─── Configuration ───────────────────────────────────────────
ADOBE_OAUTH_URL = "https://ims-na1.adobelogin.com/ims/authorize/v2"
ADOBE_TOKEN_URL = "https://ims-na1.adobelogin.com/ims/token/v3"
ADOBE_USERINFO_URL = "https://ims-na1.adobelogin.com/ims/userinfo/v2"

SCRIPT_DIR = Path(__file__).parent.resolve()
SESSION_STORE = SCRIPT_DIR / ".oauth_sessions.json"

# Default scopes for PDF Services
DEFAULT_SCOP = [
    "openid",
    "AdobeID",
    "read_organizations",
    "additional_info.projectedProductContext",
    "additional_info.roles",
]


class AdobeOAuthSession:
    """Manages a single user's OAuth session and token."""

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.access_token = None
        self.refresh_token = None
        self.token_expires = 0
        self.user_info = None

    def get_auth_url(self, state: str, scope: list = None) -> str:
        """Generate the Adobe OAuth authorization URL."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(scope or DEFAULT_SCOP),
            "state": state,
        }
        return f"{ADOBE_OAUTH_URL}?{urllib.parse.urlencode(params)}"

    def exchange_code(self, code: str) -> dict:
        """Exchange authorization code for access token."""
        resp = requests.post(
            ADOBE_TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": self.redirect_uri,
            },
        )

        if resp.status_code != 200:
            raise Exception(f"Token exchange failed ({resp.status_code}): {resp.text[:200]}")

        data = resp.json()
        self.access_token = data["access_token"]
        self.refresh_token = data.get("refresh_token")
        self.token_expires = time.time() + int(data.get("expires_in", 3600))

        # Fetch user info
        self.user_info = self._get_user_info()
        return data

    def refresh_access_token(self) -> dict:
        """Refresh an expired access token."""
        if not self.refresh_token:
            raise Exception("No refresh token available")

        resp = requests.post(
            ADOBE_TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
        )

        if resp.status_code != 200:
            raise Exception(f"Token refresh failed ({resp.status_code}): {resp.text[:200]}")

        data = resp.json()
        self.access_token = data["access_token"]
        self.refresh_token = data.get("refresh_token", self.refresh_token)
        self.token_expires = time.time() + int(data.get("expires_in", 3600))
        return data

    def _get_user_info(self) -> dict:
        """Get authenticated user info."""
        resp = requests.get(
            ADOBE_USERINFO_URL,
            headers={"Authorization": f"Bearer {self.access_token}"},
        )
        if resp.status_code != 200:
            return {"error": "Failed to get user info"}
        return resp.json()

    def is_valid(self) -> bool:
        """Check if access token is still valid."""
        return self.access_token is not None and time.time() < self.token_expires - 60

    def get_token(self) -> str:
        """Get a valid access token (refreshes if needed)."""
        if not self.is_valid():
            self.refresh_access_token()
        return self.access_token


class OAuthSessionStore:
    """Persists OAuth sessions to disk."""

    def __init__(self, store_path: Path):
        self.store_path = store_path
        self.sessions: dict[str, dict] = {}
        self._load()

    def _load(self):
        if self.store_path.exists():
            try:
                with open(self.store_path) as f:
                    self.sessions = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.sessions = {}

    def save(self):
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.store_path, "w") as f:
            json.dump(self.sessions, f, indent=2)

    def create_session(self, session_id: str) -> dict:
        self.sessions[session_id] = {
            "state": secrets.token_urlsafe(32),
            "created_at": time.time(),
            "access_token": None,
            "refresh_token": None,
            "token_expires": 0,
            "user_info": None,
        }
        self.save()
        return self.sessions[session_id]

    def get_session(self, session_id: str) -> Optional[dict]:
        return self.sessions.get(session_id)

    def update_session(self, session_id: str, token_data: dict, user_info: dict):
        if session_id not in self.sessions:
            return
        self.sessions[session_id].update({
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token"),
            "token_expires": time.time() + int(token_data.get("expires_in", 3600)),
            "user_info": user_info,
        })
        self.save()

    def delete_session(self, session_id: str):
        self.sessions.pop(session_id, None)
        self.save()

    def is_valid(self, session_id: str) -> bool:
        session = self.sessions.get(session_id)
        if not session or not session.get("access_token"):
            return False
        return time.time() < session.get("token_expires", 0) - 60


class OAuthHandler(BaseHTTPRequestHandler):
    """HTTP server for OAuth callback."""

    session_store = None
    oauth = None
    authenticated = False

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/callback":
            self._handle_callback(parsed)
        elif parsed.path == "/login":
            self._handle_login()
        elif parsed.path == "/logout":
            self._handle_logout()
        elif parsed.path == "/status":
            self._handle_status()
        elif parsed.path == "/token":
            self._handle_token()
        else:
            self.send_response(404)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>404 Not Found</h1>")

    def _handle_login(self):
        """Redirect user to Adobe OAuth."""
        session_id = secrets.token_urlsafe(32)
        session = self.session_store.create_session(session_id)

        # Set session cookie
        self.send_response(302)
        self.send_header("Set-Cookie", f"oauth_session={session_id}; Path=/; HttpOnly; SameSite=Lax")
        self.send_header("Location", self.oauth.get_auth_url(session["state"]))
        self.end_headers()

    def _handle_callback(self, parsed):
        """Handle OAuth callback from Adobe."""
        params = parse_qs(parsed.query)
        code = params.get("code", [None])[0]
        state = params.get("state", [None])[0]
        error = params.get("error", [None])[0]

        # Get session from cookie
        cookies = {}
        for cookie in self.headers.get("Cookie", "").split(";"):
            if "=" in cookie:
                k, v = cookie.strip().split("=", 1)
                cookies[k] = v

        session_id = cookies.get("oauth_session")
        if not session_id:
            self._render_error("No session found. Please try again.")
            return

        session = self.session_store.get_session(session_id)
        if not session:
            self._render_error("Invalid session. Please try again.")
            return

        # Verify state
        if state != session["state"]:
            self._render_error("Invalid state. Possible CSRF attack.")
            return

        if error:
            self._render_error(f"OAuth error: {error}")
            return

        if not code:
            self._render_error("No authorization code received.")
            return

        # Exchange code for token
        try:
            token_data = self.oauth.exchange_code(code)
            self.session_store.update_session(session_id, token_data, self.oauth.user_info)
            self.authenticated = True

            # Render success page
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            user_name = self.oauth.user_info.get("name", "User")
            user_email = self.oauth.user_info.get("email", "unknown")
            html = f"""
            <!DOCTYPE html>
            <html>
            <head><title>Adobe Auth - Success</title>
            <style>
                body {{ font-family: system-ui, sans-serif; background: #0d1117; color: #c9d1d9;
                       display: flex; align-items: center; justify-content: center;
                       min-height: 100vh; margin: 0; }}
                .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 12px;
                        padding: 2rem; text-align: center; max-width: 400px; }}
                .icon {{ font-size: 3rem; margin-bottom: 1rem; }}
                h1 {{ font-size: 1.25rem; margin-bottom: 0.5rem; }}
                p {{ color: #8b949e; font-size: 0.875rem; margin-bottom: 1rem; }}
                .close {{ background: #3fb950; color: #000; border: none; padding: 0.5rem 1.5rem;
                        border-radius: 6px; font-weight: 600; cursor: pointer; font-size: 0.875rem; }}
            </style>
            </head>
            <body>
                <div class="card">
                    <div class="icon">✅</div>
                    <h1>Successfully Signed In</h1>
                    <p>Signed in as <strong>{user_name}</strong><br>{user_email}</p>
                    <p style="font-size: 0.75rem; color: #8b949e;">
                        You can now use Adobe Cloud Auto-Tag in the PDF ADA Compliance Processor.
                    </p>
                    <button class="close" onclick="window.close()">Close This Tab</button>
                </div>
            </body>
            </html>
            """
            self.wfile.write(html.encode())
        except Exception as e:
            self._render_error(f"Token exchange failed: {str(e)}")

    def _handle_logout(self):
        """Log out and clear session."""
        cookies = {}
        for cookie in self.headers.get("Cookie", "").split(";"):
            if "=" in cookie:
                k, v = cookie.strip().split("=", 1)
                cookies[k] = v

        session_id = cookies.get("oauth_session")
        if session_id:
            self.session_store.delete_session(session_id)

        self.send_response(302)
        self.send_header("Set-Cookie", "oauth_session=; Path=/; HttpOnly; Max-Age=0")
        self.send_header("Location", "/")
        self.end_headers()

    def _handle_status(self):
        """Return auth status as JSON."""
        cookies = {}
        for cookie in self.headers.get("Cookie", "").split(";"):
            if "=" in cookie:
                k, v = cookie.strip().split("=", 1)
                cookies[k] = v

        session_id = cookies.get("oauth_session")
        if session_id and self.session_store.is_valid(session_id):
            session = self.session_store.get_session(session_id)
            user = session.get("user_info", {})
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "authenticated": True,
                "user": {
                    "name": user.get("name", "Unknown"),
                    "email": user.get("email", "unknown"),
                }
            }).encode())
        else:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"authenticated": False}).encode())

    def _handle_token(self):
        """Return the access token for the current session."""
        cookies = {}
        for cookie in self.headers.get("Cookie", "").split(";"):
            if "=" in cookie:
                k, v = cookie.strip().split("=", 1)
                cookies[k] = v

        session_id = cookies.get("oauth_session")
        if not session_id:
            self.send_response(401)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "No session"}).encode())
            return

        session = self.session_store.get_session(session_id)
        if not session or not session.get("access_token"):
            self.send_response(401)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not authenticated"}).encode())
            return

        # Refresh token if expired
        if time.time() >= session.get("token_expires", 0) - 60:
            try:
                self.oauth.access_token = session["access_token"]
                self.oauth.refresh_token = session.get("refresh_token")
                self.oauth.token_expires = session.get("token_expires", 0)
                self.oauth.refresh_access_token()
                self.session_store.update_session(
                    session_id,
                    {"access_token": self.oauth.access_token, "expires_in": 3600},
                    session.get("user_info", {})
                )
            except Exception as e:
                self.send_response(401)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Token refresh failed: {str(e)}"}).encode())
                return

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({
            "access_token": self.session_store.get_session(session_id)["access_token"]
        }).encode())

    def _render_error(self, message: str):
        self.send_response(400)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        html = f"""
        <!DOCTYPE html><html><head><title>Error</title>
        <style>
            body {{ font-family: system-ui; background: #0d1117; color: #c9d1d9;
                   display: flex; align-items: center; justify-content: center;
                   min-height: 100vh; margin: 0; }}
            .card {{ background: #161b22; border: 1px solid #f85149; border-radius: 12px;
                    padding: 2rem; text-align: center; max-width: 400px; }}
            .icon {{ font-size: 3rem; margin-bottom: 1rem; }}
            h1 {{ color: #f85149; font-size: 1.25rem; margin-bottom: 0.5rem; }}
            p {{ color: #8b949e; font-size: 0.875rem; }}
            .retry {{ background: #58a6ff; color: #fff; border: none; padding: 0.5rem 1.5rem;
                     border-radius: 6px; cursor: pointer; margin-top: 1rem; }}
        </style></head><body>
        <div class="card">
            <div class="icon">❌</div>
            <h1>Authentication Failed</h1>
            <p>{message}</p>
            <a href="/login"><button class="retry">Try Again</button></a>
        </div></body></html>
        """
        self.wfile.write(html.encode())

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


def load_oauth_config() -> tuple:
    """Load OAuth client credentials."""
    config_path = SCRIPT_DIR / "adobe_oauth_config.json"

    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
        return config["client_id"], config["client_secret"], config["redirect_uri"]

    # Interactive setup
    print("❌ No Adobe OAuth configuration found.")
    print("\n📝 To enable browser-based Adobe sign-in:")
    print("   1. Go to https://developer.adobe.com/console")
    print("   2. Create a new project")
    print("   3. Add 'Adobe ID' authentication")
    print("   4. Note your Client ID and Client Secret")
    print("   5. Set redirect URI to: http://localhost:3457/callback\n")

    client_id = input("   Client ID: ").strip()
    client_secret = input("   Client Secret: ").strip()
    redirect_uri = input("   Redirect URI (default: http://localhost:3457/callback): ").strip()
    redirect_uri = redirect_uri or "http://localhost:3457/callback"

    if not client_id or not client_secret:
        print("❌ Credentials required.")
        sys.exit(1)

    with open(config_path, "w") as f:
        json.dump({
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
        }, f, indent=2)

    print(f"\n✅ Configuration saved to {config_path}")
    return client_id, client_secret, redirect_uri


def main():
    """Start the OAuth server."""
    print("=" * 60)
    print("Adobe OAuth 2.0 Server")
    print("=" * 60)

    client_id, client_secret, redirect_uri = load_oauth_config()

    # Parse redirect URI for port
    parsed = urllib.parse.urlparse(redirect_uri)
    port = parsed.port or 3457

    oauth = AdobeOAuthSession(client_id, client_secret, redirect_uri)
    session_store = OAuthSessionStore(SESSION_STORE)

    OAuthHandler.oauth = oauth
    OAuthHandler.session_store = session_store

    server = HTTPServer(("127.0.0.1", port), OAuthHandler)
    print(f"\n🔐 OAuth server running at http://localhost:{port}")
    print(f"   Callback URL: {redirect_uri}")
    print(f"   Login URL:    http://localhost:{port}/login")
    print(f"   Status URL:   http://localhost:{port}/status")
    print(f"\n   In the PDF ADA UI, users can click 'Sign in with Adobe'")
    print(f"   to authenticate without developer credentials.\n")
    print("   Press Ctrl+C to stop.\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 OAuth server stopped.")
        server.shutdown()


if __name__ == "__main__":
    main()
