import ipaddress
import posixpath
import re
import socket
from urllib.parse import parse_qsl, quote, unquote, urlencode, urljoin, urlsplit, urlunsplit

ASSET = re.compile(
    r"\.(?:pdf|zip|gz|png|jpe?g|gif|svg|webp|ico|css|js|mp[34]|woff2?|ttf|xml|json|csv|xlsx?)(?:$)",
    re.IGNORECASE,
)


def normalize_url(value: str, base: str = "") -> str | None:
    try:
        p = urlsplit(urljoin(base, value.strip()))
        if p.scheme.lower() not in {"http", "https"} or not p.hostname or p.username or p.password:
            return None
        host = p.hostname.lower().rstrip(".").encode("idna").decode("ascii")
        port = p.port
        if port not in (None, 80 if p.scheme.lower() == "http" else 443):
            return None
        if ":" in host:
            host = f"[{host}]"
        # Decode only unreserved characters; keep encoded slashes as distinct resources.
        path = re.sub(
            r"%([0-9a-fA-F]{2})",
            lambda m: (
                chr(int(m[1], 16))
                if chr(int(m[1], 16))
                in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
                else m[0].upper()
            ),
            p.path or "/",
        )
        trailing = path.endswith("/")
        path = posixpath.normpath("/" + path.lstrip("/"))
        if trailing and path != "/":
            path += "/"
        path = quote(path, safe="/%:@!$&'()*+,;=-._~")
        query = urlencode(
            sorted(
                (k, v)
                for k, v in parse_qsl(p.query, keep_blank_values=True)
                if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid"}
            )
        )
        return urlunsplit((p.scheme.lower(), host, path, query, ""))
    except (ValueError, UnicodeError):
        return None


def under_prefix(url: str, prefix: str) -> bool:
    normalized = normalize_url(prefix)
    if not normalized:
        return False
    u, p = urlsplit(url), urlsplit(normalized)
    return (u.scheme, u.netloc) == (p.scheme, p.netloc) and (
        u.path == p.path.rstrip("/") or u.path.startswith(p.path.rstrip("/") + "/")
    )


def in_scope(url: str, settings) -> bool:
    return (
        urlsplit(url).hostname in settings.allowed_domains
        and not ASSET.search(unquote(urlsplit(url).path))
        and (not settings.url_prefixes or any(under_prefix(url, p) for p in settings.url_prefixes))
        and not any(under_prefix(url, p) for p in settings.denied_prefixes)
    )


def require_public_url(url: str):
    """Defense in depth against accidental access to local/private services."""
    p = urlsplit(url)
    if not normalize_url(url):
        raise ValueError("invalid public HTTP URL")
    addresses = socket.getaddrinfo(
        p.hostname, p.port or (443 if p.scheme == "https" else 80), type=socket.SOCK_STREAM
    )
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise ValueError("non-public network destination rejected")
