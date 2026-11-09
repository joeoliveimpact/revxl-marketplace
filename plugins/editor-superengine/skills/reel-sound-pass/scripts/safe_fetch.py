"""Bounded downloads with every redirect checked; conservative collision names."""
import ipaddress
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request


class Refused(ValueError):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def check_url(url, *, first=False):
    u = urllib.parse.urlsplit(url)
    if u.scheme.lower() == "file" and first:
        local = urllib.parse.unquote(u.path).replace("\\", "/")
        if u.netloc not in ("", "localhost") or local.startswith("//") or "\x00" in local:
            raise Refused("The sound pack file must be on this computer.")
        return
    if u.scheme.lower() not in ("http", "https") or not u.hostname:
        raise Refused("The sound pack needs an http or https download link.")
    if u.username is not None or u.password is not None:
        raise Refused("The sound pack link must not contain login details.")
    host = u.hostname.rstrip(".").lower()
    if "%" in host or host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        raise Refused("The sound pack link points to a local or private host.")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        # Reject alternate numeric IPv4 spellings rather than letting a URL
        # library resolve 127.1, octal or integer addresses behind this check.
        if all(re.fullmatch(r"(?:[0-9]+|0x[0-9a-f]+)", label) for label in host.split(".")):
            raise Refused("The sound pack link has an ambiguous numeric host.")
    else:
        if not ip.is_global:
            raise Refused("The sound pack link points to a local or private address.")
    # ponytail: DNS names are trusted here. This is a literal-host policy;
    # it does not resolve names or prevent DNS rebinding.


def send(url):
    try:
        return urllib.request.build_opener(_NoRedirect()).open(url, timeout=300)
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307, 308):
            return e
        raise


def download(url, dest, cap, *, send=None):
    """Write at most cap bytes. Delete dest on every refusal or read failure.

    send(url) is injectable for offline tests and returns a context manager
    with headers, status (or code), and read(n).
    """
    dest = Path(dest)
    if type(cap) is not int or cap < 0:
        dest.unlink(missing_ok=True)
        raise Refused("The sound pack manifest needs a non-negative byte limit.")
    transport = send or globals()["send"]
    try:
        for hop in range(6):
            check_url(url, first=hop == 0)
            with transport(url) as response:
                status = getattr(response, "status", None) or getattr(response, "code", None) or 200
                if status in (301, 302, 303, 307, 308):
                    location = response.headers.get("Location")
                    if not location or hop == 5:
                        raise Refused("The sound pack link redirected too many times or has no destination.")
                    url = urllib.parse.urljoin(url, location)
                    continue
                if status != 200:
                    raise Refused("The sound pack server did not return a download.")
                if (response.headers.get("Content-Type") or "").split(";")[0].strip().lower() == "text/html":
                    raise Refused("The download link opened a web page, not the sound pack, so nothing was unpacked.")
                size = response.headers.get("Content-Length")
                if size is not None and (int(size) < 0 or int(size) > cap):
                    raise Refused("The sound pack is larger than its manifest byte limit.")
                total = 0
                with dest.open("wb") as out:
                    while True:
                        # Read only one byte past the limit, even without a length.
                        chunk = response.read(min(65536, cap - total + 1))
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > cap:
                            raise Refused("The sound pack stream passed its manifest byte limit.")
                        out.write(chunk)
                return total
        raise Refused("The sound pack link redirected too many times.")
    except BaseException:
        dest.unlink(missing_ok=True)
        raise


def free_name(path):
    """Return the first unused name; never claim an existing file is ours."""
    path = Path(path)
    if not path.exists() and not path.is_symlink():
        return path
    n = 2
    while True:
        candidate = path.with_name(f"{path.stem}-{n}{path.suffix}")
        if not candidate.exists() and not candidate.is_symlink():
            print(f"Kept {path.name} (yours); writing {candidate.name} instead.")
            return candidate
        n += 1


def write_new(path, data):
    """Exclusive creation closes the gap between choosing a name and writing."""
    while True:
        dest = free_name(path)
        try:
            with dest.open("xb") as out:
                out.write(data)
            return dest
        except FileExistsError:
            continue
