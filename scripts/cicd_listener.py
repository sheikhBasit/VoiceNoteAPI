import http.server
import socketserver
import subprocess
import os
import json
import hmac
import hashlib

# --- CONFIGURATION ---
PORT = 9000
SECRET_TOKEN = "replace_with_your_secure_random_token"
DEPLOY_SCRIPT = "/home/azureuser/voicenote-api/scripts/server_update.sh"
# ---------------------

class WebhookHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        # 1. Verify URL
        if self.path != "/webhook/deploy":
            self.send_response(404)
            self.end_headers()
            return

        # 2. Verify Signature (GitHub sends X-Hub-Signature-256)
        content_len = int(self.headers.get('content-length', 0))
        body = self.rfile.read(content_len)
        signature = self.headers.get('X-Hub-Signature-256')

        if not self.verify_signature(body, signature):
            print("❌ Invalid signature")
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b"Forbidden: Invalid Signature")
            return

        # 3. Handle Event (Optional: Check specific branch)
        print("✅ Received valid deployment trigger!")
        
        # 4. Trigger Deployment Script
        try:
            # Run non-blocking or blocking? Blocking simpler for now.
            result = subprocess.run(
                [DEPLOY_SCRIPT], 
                check=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            print("🚀 Deployment Output:\n", result.stdout)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Deployment Triggered Successfully")
        except subprocess.CalledProcessError as e:
            print("❌ Deployment Failed:\n", e.stderr)
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Deployment Failed: {e.stderr}".encode())

    def verify_signature(self, body, signature):
        if not signature: 
            return False # Enforce security
        
        # GitHub signature format: sha256=....
        if not signature.startswith("sha256="):
            return False
            
        params = signature.split("=")
        if len(params) != 2:
            return False

        expected_hash = hmac.new(
            SECRET_TOKEN.encode(), 
            body, 
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(params[1], expected_hash)

if __name__ == "__main__":
    print(f"👂 CICD Listener started on port {PORT}...")
    with socketserver.TCPServer(("", PORT), WebhookHandler) as httpd:
        httpd.serve_forever()
