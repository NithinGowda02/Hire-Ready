import socket
from app import create_app, db

# Force IPv4-only DNS resolution to avoid Render's IPv6 routing issue with Neon
_orig_getaddrinfo = socket.getaddrinfo

def _ipv4_only_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)

socket.getaddrinfo = _ipv4_only_getaddrinfo

app = create_app()

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run()