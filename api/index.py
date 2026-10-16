from http.server import BaseHTTPRequestHandler
import json
import hashlib
import hmac
import os
import time
import threading
from urllib.parse import urlparse, parse_qs

# Vercel Python serverless function.
# Note: in-memory messages/rooms are not durable across serverless invocations.
# This demo uses a process-local store for simple testing only.
ROOM_SECRET = os.environ.get("ROOM_SECRET", "change-this-secret-before-deploying")
ROOMS = {}
LOCK = threading.Lock()
MAX_MESSAGES = 100

def room_key(password):
    return hmac.new(ROOM_SECRET.encode(), password.encode(), hashlib.sha256).hexdigest()

def json_bytes(payload):
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")

class handler(BaseHTTPRequestHandler):
    def _send(self, status, payload):
        body = json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send(200, {"ok": True})

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path.endswith("/api") or parsed.path == "/api/":
            return self._send(200, {"ok": True, "name": "DEVIL CHATS", "message": "API is running"})
        if parsed.path.endswith("/messages"):
            query = parse_qs(parsed.query)
            password = query.get("password", [""])[0]
            if not 8 <= len(password) <= 128:
                return self._send(400, {"ok": False, "error": "Passphrase must be 8–128 characters."})
            key = room_key(password)
            with LOCK:
                room = ROOMS.get(key, {"members": {}, "messages": []})
                result = {"ok": True, "messages": room["messages"][-MAX_MESSAGES:]}
            return self._send(200, result)
        return self._send(404, {"ok": False, "error": "Not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 12000:
                return self._send(413, {"ok": False, "error": "Request too large."})
            data = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return self._send(400, {"ok": False, "error": "Invalid JSON."})

        if parsed.path.endswith("/join"):
            username = str(data.get("username", "")).strip()[:24]
            password = data.get("password", "")
            if not isinstance(password, str) or not 8 <= len(password) <= 128:
                return self._send(400, {"ok": False, "error": "Passphrase must be 8–128 characters."})
            if not (2 <= len(username) <= 24) or not all(ch.isalnum() or ch in "_-" for ch in username):
                return self._send(400, {"ok": False, "error": "Username must be 2–24 letters, numbers, _ or -."})
            key = room_key(password)
            with LOCK:
                room = ROOMS.setdefault(key, {"members": {}, "messages": []})
                # Membership is best-effort only on serverless because instances are ephemeral.
                if username.lower() in (name.lower() for name in room["members"].values()):
                    return self._send(409, {"ok": False, "error": "That username is already connected in this room."})
                if len(room["members"]) >= 2:
                    return self._send(409, {"ok": False, "error": "This room already has two connected users."})
                token = hashlib.sha256(f"{username}:{time.time_ns()}".encode()).hexdigest()
                room["members"][token] = username
                waiting = len(room["members"]) == 1
            return self._send(200, {"ok": True, "username": username, "token": token, "waiting": waiting})

        if parsed.path.endswith("/send"):
            username = str(data.get("username", "Guest"))[:24]
            password = data.get("password", "")
            message = str(data.get("message", "")).strip()
            if not isinstance(password, str) or not 8 <= len(password) <= 128:
                return self._send(400, {"ok": False, "error": "Passphrase must be 8–128 characters."})
            if not message or len(message) > 2000:
                return self._send(400, {"ok": False, "error": "Message must be 1–2000 characters."})
            key = room_key(password)
            item = {"username": username, "message": message, "time": int(time.time())}
            with LOCK:
                room = ROOMS.setdefault(key, {"members": {}, "messages": []})
                room["messages"].append(item)
                room["messages"] = room["messages"][-MAX_MESSAGES:]
            return self._send(200, {"ok": True, "message": item})

        return self._send(404, {"ok": False, "error": "Unknown endpoint."})

    def log_message(self, format, *args):
        # Avoid logging request details, which may contain sensitive information.
        return
