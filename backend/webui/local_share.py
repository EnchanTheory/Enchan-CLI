"""Fail-closed local LAN sharing for the Enchan Web UI."""

from __future__ import annotations

import base64
import ctypes
import hashlib
import hmac
import ipaddress
import io
import json
import os
import re
import secrets
import socket
import ssl
import tempfile
import subprocess
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable


PBKDF2_ITERATIONS = 240_000
REMOTE_IDLE_SECONDS = 45.0
NETWORK_CHECK_SECONDS = 2.0
SLEEP_GAP_SECONDS = 8.0
SESSION_MAX_AGE_SECONDS = 30 * 60
TLS_CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "local-share-tls"
TLS_CERTIFICATE_DAYS = 397


class LocalShareError(RuntimeError):
    """A local share request was refused or could not be completed."""


@dataclass(frozen=True)
class NetworkSnapshot:
    ssid: str
    ip: str
    adapter: str
    interface_index: int
    prefix_length: int
    category: str
    transport: str
    authentication: str
    cipher: str

    def public_dict(self) -> dict[str, Any]:
        return {
            "ssid": self.ssid,
            "ip": self.ip,
            "adapter": self.adapter,
            "networkType": self.category,
            "connectionType": self.transport,
            "authentication": self.authentication,
            "cipher": self.cipher,
        }


def _run_powershell_json(script: str) -> Any:
    try:
        completed = subprocess.run(
            [
                "powershell.exe",
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                "[Console]::OutputEncoding=[Text.UTF8Encoding]::new(); " + script,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired as exc:
        raise LocalShareError("Windows network verification timed out") from exc
    if completed.returncode != 0:
        raise LocalShareError("Windows could not verify the current network profile")
    try:
        return json.loads(completed.stdout.lstrip("\ufeff").strip())
    except json.JSONDecodeError as exc:
        raise LocalShareError("Windows returned an unreadable network profile") from exc


def _adapter_transport(item: dict[str, Any]) -> str:
    medium = str(item.get("medium", "")).strip().lower()
    description = str(item.get("adapterDescription", "")).lower()
    is_wifi = medium in {"9", "ndisphysicalmediumnative802_11"}
    is_wifi = is_wifi or any(marker in medium for marker in ("802.11", "wireless lan", "native wifi"))
    is_wifi = is_wifi or any(marker in description for marker in ("wi-fi", "wifi", "wireless", "802.11"))
    if is_wifi:
        return "wifi"
    is_ethernet = medium in {"14", "ndisphysicalmedium802_3"}
    is_ethernet = is_ethernet or any(marker in medium for marker in ("802.3", "802_3", "ethernet"))
    return "ethernet" if is_ethernet else ""


def _verified_wifi_security(wlan: str) -> tuple[str, str, str]:
    if re.search(r"\b(open|wep|none)\b", wlan, flags=re.IGNORECASE):
        raise LocalShareError("The Wi-Fi network is open or uses unsupported encryption")
    ssids = re.findall(r"(?mi)^\s*SSID\s*:\s*(.+?)\s*$", wlan)
    authentication = re.findall(r"\bWPA(?:2|3)(?:-[A-Za-z]+)?\b", wlan, flags=re.IGNORECASE)
    ciphers = re.findall(r"\b(?:CCMP|GCMP(?:-256)?|AES)\b", wlan, flags=re.IGNORECASE)
    if len(ssids) != 1 or not ssids[0].strip() or not authentication or not ciphers:
        raise LocalShareError("WPA2-AES or WPA3 Wi-Fi security could not be verified")
    auth = authentication[0].upper()
    cipher = ciphers[0].upper()
    if auth.startswith("WPA2") and cipher not in {"AES", "CCMP"}:
        raise LocalShareError("WPA2 Wi-Fi must use AES/CCMP encryption")
    if not auth.startswith(("WPA2", "WPA3")):
        raise LocalShareError("Wi-Fi must use WPA2-AES or WPA3")
    return ssids[0].strip(), auth, cipher


def inspect_safe_network() -> NetworkSnapshot:
    """Return one approved physical Ethernet or private WPA2/3 Wi-Fi network."""
    if os.name != "nt":
        raise LocalShareError("Local sharing currently requires Windows network security APIs")
    script = r"""
$ErrorActionPreference = 'Stop'
$items = @()
foreach ($profile in @(Get-NetConnectionProfile)) {
  if ([string]$profile.IPv4Connectivity -eq 'Disconnected') { continue }
  $adapter = Get-NetAdapter -InterfaceIndex $profile.InterfaceIndex -ErrorAction Stop
  $addresses = @(Get-NetIPAddress -InterfaceIndex $profile.InterfaceIndex -AddressFamily IPv4 -ErrorAction Stop |
    Where-Object { $_.AddressState -eq 'Preferred' -and $_.IPAddress -notlike '169.254.*' -and $_.IPAddress -ne '127.0.0.1' })
  foreach ($address in $addresses) {
    $items += [pscustomobject]@{
      name = [string]$profile.Name
      category = [string]$profile.NetworkCategory
      ipv4Connectivity = [string]$profile.IPv4Connectivity
      interfaceIndex = [int]$profile.InterfaceIndex
      adapterName = [string]$adapter.Name
      adapterDescription = [string]$adapter.InterfaceDescription
      adapterStatus = [string]$adapter.Status
      hardware = [bool]$adapter.HardwareInterface
      medium = [string]$adapter.NdisPhysicalMedium
      ip = [string]$address.IPAddress
      prefixLength = [int]$address.PrefixLength
    }
  }
}
$wlan = (& netsh.exe wlan show interfaces 2>&1 | Out-String)
[pscustomobject]@{ items = $items; wlan = $wlan } | ConvertTo-Json -Depth 5 -Compress
"""
    result = _run_powershell_json(script)
    items = result.get("items", []) if isinstance(result, dict) else []
    if isinstance(items, dict):
        items = [items]
    candidates: list[tuple[dict[str, Any], str]] = []
    for item in items if isinstance(items, list) else []:
        transport = _adapter_transport(item)
        category = str(item.get("category", "")).strip().lower()
        if (
            transport
            and str(item.get("adapterStatus", "")).lower() == "up"
            and item.get("hardware") is True
            and category in {"private", "public", "domainauthenticated"}
            and (transport == "ethernet" or category == "private")
        ):
            candidates.append((item, transport))
    if len(candidates) != 1:
        raise LocalShareError("A single supported physical LAN adapter could not be verified")

    item, transport = candidates[0]
    category = str(item.get("category", "")).strip()
    network_name = str(item.get("name", "")).strip()
    authentication = "WIRED"
    cipher = "802.3"
    if transport == "wifi":
        network_name, authentication, cipher = _verified_wifi_security(str(result.get("wlan", "")))

    ip = str(item.get("ip", "")).strip()
    adapter = str(item.get("adapterName", "")).strip()
    try:
        parsed_ip = ipaddress.IPv4Address(ip)
        prefix_length = int(item["prefixLength"])
    except (ipaddress.AddressValueError, KeyError, TypeError, ValueError) as exc:
        raise LocalShareError("The LAN IPv4 address could not be verified") from exc
    if (
        not network_name
        or not adapter
        or not parsed_ip.is_private
        or parsed_ip.is_loopback
        or parsed_ip.is_link_local
        or parsed_ip.is_unspecified
        or not 1 <= prefix_length <= 32
    ):
        raise LocalShareError("Adapter or private IPv4 address could not be verified")
    return NetworkSnapshot(
        ssid=network_name,
        ip=ip,
        adapter=adapter,
        interface_index=int(item["interfaceIndex"]),
        prefix_length=prefix_length,
        category=category,
        transport=transport,
        authentication=authentication,
        cipher=cipher,
    )


def network_matches(expected: NetworkSnapshot) -> bool:
    """Quickly revalidate a previously approved adapter without a slow IP query."""
    if os.name != "nt":
        return False
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.bind((expected.ip, 0))
    except OSError:
        return False
    finally:
        probe.close()
    script = rf"""
$ErrorActionPreference = 'Stop'
$profile = Get-NetConnectionProfile -InterfaceIndex {expected.interface_index} -ErrorAction Stop
$adapter = Get-NetAdapter -InterfaceIndex {expected.interface_index} -ErrorAction Stop
$address = Get-NetIPAddress -InterfaceIndex {expected.interface_index} -AddressFamily IPv4 -IPAddress '{expected.ip}' -ErrorAction Stop
$wlan = (& netsh.exe wlan show interfaces 2>&1 | Out-String)
[pscustomobject]@{{
  name = [string]$profile.Name
  ip = [string]$address.IPAddress
  prefixLength = [int]$address.PrefixLength
  addressState = [string]$address.AddressState
  category = [string]$profile.NetworkCategory
  adapterName = [string]$adapter.Name
  adapterDescription = [string]$adapter.InterfaceDescription
  adapterStatus = [string]$adapter.Status
  hardware = [bool]$adapter.HardwareInterface
  medium = [string]$adapter.NdisPhysicalMedium
  wlan = $wlan
}} | ConvertTo-Json -Compress
"""
    try:
        result = _run_powershell_json(script)
    except LocalShareError:
        return False
    if not isinstance(result, dict):
        return False
    stable = bool(
        _adapter_transport(result) == expected.transport
        and str(result.get("ip", "")).strip() == expected.ip
        and result.get("prefixLength") == expected.prefix_length
        and str(result.get("addressState", "")).strip().lower() == "preferred"
        and str(result.get("category", "")).strip().lower() == expected.category.lower()
        and str(result.get("adapterName", "")).strip() == expected.adapter
        and str(result.get("adapterStatus", "")).lower() == "up"
        and result.get("hardware") is True
    )
    if not stable:
        return False
    if expected.transport == "ethernet":
        return str(result.get("name", "")).strip() == expected.ssid
    try:
        ssid, authentication, cipher = _verified_wifi_security(str(result.get("wlan", "")))
    except LocalShareError:
        return False
    return bool(
        ssid == expected.ssid
        and authentication == expected.authentication
        and cipher == expected.cipher
        and str(result.get("category", "")).lower() == "private"
    )

def _password_hash(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("ascii"), salt, PBKDF2_ITERATIONS)


def _token_hash(token: str) -> bytes:
    return hashlib.sha256(token.encode("ascii")).digest()


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_ulong), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def _dpapi_crypt(data: bytes, *, decrypt: bool) -> bytes:
    """Protect the persistent MOBILE private key for the current Windows user."""
    if os.name != "nt":
        raise LocalShareError("Persistent MOBILE TLS keys require Windows DPAPI")
    source = ctypes.create_string_buffer(data)
    source_blob = _DataBlob(len(data), ctypes.cast(source, ctypes.POINTER(ctypes.c_ubyte)))
    output_blob = _DataBlob()
    crypt32 = ctypes.windll.crypt32
    function = crypt32.CryptUnprotectData if decrypt else crypt32.CryptProtectData
    ok = function(
        ctypes.byref(source_blob), None, None, None, None, 1, ctypes.byref(output_blob)
    )
    if not ok:
        raise LocalShareError("Windows could not protect the MOBILE TLS private key")
    try:
        return ctypes.string_at(output_blob.pbData, output_blob.cbData)
    finally:
        kernel32 = ctypes.windll.kernel32
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        kernel32.LocalFree.restype = ctypes.c_void_p
        kernel32.LocalFree(ctypes.cast(output_blob.pbData, ctypes.c_void_p))


def _tls_cache_path(ip: str) -> Path:
    safe_ip = str(ipaddress.IPv4Address(ip)).replace(".", "-")
    return TLS_CACHE_DIR / f"{safe_ip}.json"


def _load_tls_material(ip: str) -> tuple[bytes, bytes] | None:
    path = _tls_cache_path(ip)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("version") != 2 or payload.get("ip") != ip:
            return None
        certificate = base64.b64decode(payload["certificate"], validate=True)
        protected_key = base64.b64decode(payload["protectedPrivateKey"], validate=True)
        return certificate, _dpapi_crypt(protected_key, decrypt=True)
    except Exception:
        return None


def _save_tls_material(ip: str, certificate: bytes, private_key: bytes) -> None:
    TLS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 2,
        "ip": ip,
        "certificate": base64.b64encode(certificate).decode("ascii"),
        "protectedPrivateKey": base64.b64encode(
            _dpapi_crypt(private_key, decrypt=False)
        ).decode("ascii"),
    }
    path = _tls_cache_path(ip)
    temporary = path.with_suffix(f".{secrets.token_hex(8)}.tmp")
    try:
        temporary.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _tls_material_valid(ip: str, material: tuple[bytes, bytes], x509: Any,
                        serialization: Any, name_oid: Any) -> bool:
    try:
        certificate = x509.load_pem_x509_certificate(material[0])
        if certificate.subject != certificate.issuer:
            return False
        common_names = certificate.subject.get_attributes_for_oid(name_oid.COMMON_NAME)
        if len(common_names) != 1 or common_names[0].value != ip:
            return False
        certificate_ips = certificate.extensions.get_extension_for_class(
            x509.SubjectAlternativeName
        ).value.get_values_for_type(x509.IPAddress)
        expires = getattr(certificate, "not_valid_after_utc", None)
        if expires is None:
            expires = certificate.not_valid_after.replace(tzinfo=timezone.utc)
        private_key = serialization.load_pem_private_key(material[1], password=None)
        certificate_key = certificate.public_key().public_bytes(
            serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        private_key_public = private_key.public_key().public_bytes(
            serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return bool(
            ipaddress.ip_address(ip) in certificate_ips
            and expires > datetime.now(timezone.utc) + timedelta(days=1)
            and hmac.compare_digest(certificate_key, private_key_public)
        )
    except Exception:
        return False


def _create_tls_context(ip: str) -> ssl.SSLContext:
    """Load or create one stable direct self-signed certificate for the LAN IP."""
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
    except ImportError as exc:
        raise LocalShareError(
            "TLS support is unavailable; reinstall Enchan CLI dependencies"
        ) from exc

    material = _load_tls_material(ip)
    if material is not None and not _tls_material_valid(ip, material, x509, serialization, NameOID):
        material = None
    if material is None:
        server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        now = datetime.now(timezone.utc)
        server_subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, ip)])
        server_certificate = (
            x509.CertificateBuilder()
            .subject_name(server_subject)
            .issuer_name(server_subject)
            .public_key(server_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=5))
            .not_valid_after(now + timedelta(days=TLS_CERTIFICATE_DAYS))
            .add_extension(
                x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address(ip))]),
                critical=False,
            )
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(
                x509.SubjectKeyIdentifier.from_public_key(server_key.public_key()),
                critical=False,
            )
            .add_extension(
                x509.AuthorityKeyIdentifier.from_issuer_public_key(server_key.public_key()),
                critical=False,
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    content_commitment=False,
                    key_encipherment=True,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=False,
                    crl_sign=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .add_extension(
                x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False
            )
            .sign(server_key, hashes.SHA256())
        )
        material = (
            server_certificate.public_bytes(serialization.Encoding.PEM),
            server_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            ),
        )
        _save_tls_material(ip, *material)

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.set_alpn_protocols(["http/1.1"])
    with tempfile.TemporaryDirectory(prefix="enchan-local-tls-") as directory:
        cert_path = Path(directory, "server-certificate.pem")
        key_path = Path(directory, "private-key.pem")
        cert_path.write_bytes(material[0])
        key_path.write_bytes(material[1])
        try:
            context.load_cert_chain(certfile=cert_path, keyfile=key_path)
        except (OSError, ssl.SSLError) as exc:
            raise LocalShareError("The MOBILE TLS identity could not be loaded") from exc
    return context

def _set_console_title(title: str) -> None:
    if os.name == "nt":
        try:
            ctypes.windll.kernel32.SetConsoleTitleW(title)
        except Exception:
            pass


class LocalShareManager:
    """Owns the temporary LAN listener, credentials, and safety watchdog."""

    def __init__(self, server_factory: Callable[..., Any],
                 on_stop: Callable[[str], None] | None = None,
                 localize: Callable[..., str] | None = None) -> None:
        self._server_factory = server_factory
        self._on_stop = on_stop or (lambda _reason: None)
        self._localize = localize or (lambda _locale, key, **_values: key)
        self._locale = "en"
        self._lock = threading.RLock()
        self._server: Any | None = None
        self._thread: threading.Thread | None = None
        self._watchdog_stop: threading.Event | None = None
        self._snapshot: NetworkSnapshot | None = None
        self._url = ""
        self._password_salt = b""
        self._password_digest = b""
        self._session_digest = b""
        self._session_ip = ""
        self._session_expires = 0.0
        self._remote_last_seen = 0.0
        self._remote_ever_connected = False
        self._login_attempts: dict[str, list[float]] = {}
        self._background_body = b""
        self._background_content_type = ""
        self._stop_reason = ""

    def _text(self, key: str, **values: Any) -> str:
        return self._localize(self._locale, key, **values)

    @property
    def active(self) -> bool:
        with self._lock:
            return self._server is not None

    def start(self, locale: str = "en") -> dict[str, Any]:
        snapshot = inspect_safe_network()
        tls_context = _create_tls_context(snapshot.ip)

        password = f"{secrets.randbelow(10_000):04d}"
        salt = secrets.token_bytes(16)
        digest = _password_hash(password, salt)
        with self._lock:
            if self._server is not None:
                raise LocalShareError("Local sharing is already active")
            server = None
            for _ in range(24):
                random_port = 49_152 + secrets.randbelow(65_536 - 49_152)
                try:
                    server = self._server_factory(
                        (snapshot.ip, random_port), self, tls_context
                    )

                    break
                except OSError:
                    if server is not None:
                        server.server_close()
                        server = None
                    continue
            if server is None:
                raise LocalShareError("A free random local port could not be allocated")
            port = int(server.server_address[1])
            self._server = server
            self._snapshot = snapshot
            self._url = f"https://{snapshot.ip}:{port}/"
            self._password_salt = salt
            self._password_digest = digest
            self._session_digest = b""
            self._session_ip = ""
            self._session_expires = 0.0
            self._remote_last_seen = 0.0
            self._remote_ever_connected = False
            self._login_attempts.clear()
            self._stop_reason = ""
            self._locale = locale
            self._watchdog_stop = threading.Event()
            self._thread = threading.Thread(
                target=server.serve_forever,
                kwargs={"poll_interval": 0.25},
                name="enchan-local-share-server",
                daemon=True,
            )
            self._thread.start()
            threading.Thread(
                target=self._watch_network,
                name="enchan-local-share-watchdog",
                daemon=True,
            ).start()
        _set_console_title(self._text("localShare.consoleTitle"))
        print("\n" + "!" * 68)
        print(self._text("localShare.consoleActive", url=self._url, connected=0, max=1))
        print(self._text("localShare.consoleNetworkWatch"))
        print("!" * 68 + "\n")
        payload = self.status(include_private=True)
        payload["password"] = password
        return payload

    def stop(self, reason: str = "manual") -> None:
        with self._lock:
            server = self._server
            watchdog_stop = self._watchdog_stop
            self._server = None
            self._watchdog_stop = None
            self._snapshot = None
            self._url = ""
            self._password_salt = b""
            self._password_digest = b""
            self._session_digest = b""
            self._session_ip = ""
            self._session_expires = 0.0
            self._remote_last_seen = 0.0
            self._remote_ever_connected = False
            self._login_attempts.clear()
            self._background_body = b""
            self._background_content_type = ""
            self._stop_reason = reason
        if watchdog_stop is not None:
            watchdog_stop.set()
        if server is not None:
            try:
                self._on_stop(reason)
            except Exception:
                pass
            def close_listener() -> None:
                server.shutdown()
                close_connections = getattr(server, "close_active_connections", None)
                if close_connections is not None:
                    close_connections()
                server.server_close()
            threading.Thread(
                target=close_listener, name="enchan-local-share-stop", daemon=True
            ).start()
            reason_text = self._text(f"localShare.stopReason.{reason}")
            if reason_text == f"localShare.stopReason.{reason}":
                reason_text = reason
            print("\n" + self._text("localShare.consoleStopped", reason=reason_text) + "\n")
        _set_console_title("Enchan CLI")

    def status(self, *, include_private: bool = False) -> dict[str, Any]:
        with self._lock:
            active = self._server is not None
            connected = bool(
                active and self._session_digest and time.monotonic() < self._session_expires
            )
            payload = {
                "active": active,
                "url": self._url if active else "",
                "connectedCount": 1 if connected else 0,
                "deviceIp": self._session_ip if connected else "",
                "maxDevices": 1,
                "stopReason": self._stop_reason,
                "controller": include_private,
            }
            if active and self._snapshot is not None:
                payload["network"] = self._snapshot.public_dict()
            if not include_private:
                payload.pop("url", None)
                payload.pop("network", None)
            return payload

    def qr_png(self) -> bytes:
        with self._lock:
            if not self._url:
                raise LocalShareError("Local sharing is not active")
            url = self._url
        try:
            import qrcode
        except ImportError as exc:
            raise LocalShareError("QR support is unavailable; reinstall Enchan CLI dependencies") from exc
        image = qrcode.make(url)
        output = io.BytesIO()
        image.save(output, format="PNG")
        return output.getvalue()

    def set_background(self, body: bytes, content_type: str) -> None:
        if content_type not in {"image/png", "image/jpeg", "image/webp"}:
            raise LocalShareError("Unsupported background image type")
        with self._lock:
            if self._server is None:
                raise LocalShareError("Local sharing is not active")
            self._background_body = body
            self._background_content_type = content_type

    def clear_background(self) -> None:
        with self._lock:
            self._background_body = b""
            self._background_content_type = ""

    def background(self) -> tuple[bytes, str]:
        with self._lock:
            return self._background_body, self._background_content_type

    def validate_host(self, host: str) -> bool:
        with self._lock:
            expected = self._url.split("://", 1)[-1].rstrip("/")
        return bool(expected and hmac.compare_digest(host.strip().lower(), expected.lower()))

    def _client_is_local(self, ip: str) -> bool:
        with self._lock:
            snapshot = self._snapshot
        if snapshot is None:
            return True
        try:
            client_ip = ipaddress.IPv4Address(ip)
            network = ipaddress.IPv4Network(
                f"{snapshot.ip}/{snapshot.prefix_length}", strict=False
            )
        except (ipaddress.AddressValueError, ValueError):
            return False
        return client_ip in network and client_ip != ipaddress.IPv4Address(snapshot.ip)

    def login(self, password: str, ip: str) -> str:
        now = time.monotonic()
        if not self._client_is_local(ip):
            raise LocalShareError("The device is not on the verified local network")
        with self._lock:
            if self._server is None:
                raise LocalShareError("Local sharing is not active")
            attempts = [stamp for stamp in self._login_attempts.get(ip, []) if now - stamp < 300]
            if len(attempts) >= 5:
                raise LocalShareError("Too many login attempts; try again later")
            attempts.append(now)
            self._login_attempts[ip] = attempts
            valid = len(password) == 4 and password.isascii() and password.isdigit()
            valid = valid and hmac.compare_digest(
                _password_hash(password, self._password_salt), self._password_digest
            )
            if not valid:
                raise LocalShareError("The password is incorrect")
            if self._session_ip and self._session_ip != ip and now < self._session_expires:
                raise LocalShareError("Another device is already connected")
            token = secrets.token_urlsafe(32)
            self._session_digest = _token_hash(token)
            self._session_ip = ip
            self._session_expires = now + SESSION_MAX_AGE_SECONDS
            self._remote_last_seen = now
            self._remote_ever_connected = True
            self._login_attempts.pop(ip, None)
            return token

    def authenticate(self, token: str, ip: str, *, touch: bool = True) -> bool:
        now = time.monotonic()
        if not self._client_is_local(ip):
            return False
        with self._lock:
            valid = bool(
                self._server is not None
                and self._session_digest
                and self._session_ip == ip
                and now < self._session_expires
                and token
                and hmac.compare_digest(_token_hash(token), self._session_digest)
            )
            if valid and touch:
                self._remote_last_seen = now
                self._session_expires = now + SESSION_MAX_AGE_SECONDS
            return valid

    def logout(self) -> None:
        with self._lock:
            self._session_digest = b""
            self._session_ip = ""
            self._session_expires = 0.0

    def _watch_network(self) -> None:
        previous = time.monotonic()
        next_console_notice = previous + 30
        while True:
            with self._lock:
                stop_event = self._watchdog_stop
                expected = self._snapshot
                remote_ever = self._remote_ever_connected
                last_seen = self._remote_last_seen
                connected_ip = self._session_ip
            if stop_event is None or stop_event.wait(NETWORK_CHECK_SECONDS):
                return
            now = time.monotonic()
            if now - previous > SLEEP_GAP_SECONDS:
                self.stop("computer_sleep_or_pause")
                return
            previous = now
            if expected is None or not network_matches(expected):
                self.stop("network_changed_or_unverifiable")
                return
            if remote_ever and last_seen and now - last_seen > REMOTE_IDLE_SECONDS:
                self.stop("remote_device_inactive")
                return
            if now >= next_console_notice:
                print(self._text(
                    "localShare.consoleActive", url=self._url,
                    connected=1 if connected_ip else 0, max=1,
                ))
                next_console_notice = now + 30


def cookie_token(cookie_header: str) -> str:
    for part in cookie_header.split(";"):
        name, separator, value = part.strip().partition("=")
        if separator and name == "enchan_share_session":
            return value
    return ""


def login_page() -> bytes:
    return """<!doctype html><html lang=\"ja\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>Enchan Local</title><style>body{margin:0;background:#10141c;color:#f5f7fb;font:16px system-ui;display:grid;min-height:100vh;place-items:center}.card{width:min(88vw,360px);padding:28px;border:1px solid #394154;border-radius:18px;background:#191f2b;box-shadow:0 20px 60px #0008}h1{font-size:22px}p{color:#b9c0cf;line-height:1.6}input,button{box-sizing:border-box;width:100%;padding:14px;margin-top:12px;border-radius:10px;font:inherit}input{background:#0f131b;color:white;border:1px solid #4c566d;text-align:center;font-size:24px;letter-spacing:.35em}button{border:0;background:#8d7cff;color:#fff;font-weight:700}#error{color:#ff8f9b;min-height:1.5em}</style></head><body><main class=\"card\"><h1>Enchan ローカル配信</h1><p>PC画面に表示された4桁のパスワードを入力してください。</p><form id=\"login\"><input id=\"password\" type=\"password\" inputmode=\"numeric\" pattern=\"[0-9]{4}\" maxlength=\"4\" autocomplete=\"one-time-code\" required autofocus><button>接続</button><p id=\"error\" role=\"alert\"></p></form></main><script>login.onsubmit=async e=>{e.preventDefault();error.textContent='';const r=await fetch('/api/local-share/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:password.value})});if(r.ok)location.replace(new URL("/",location.href).href);else{const d=await r.json().catch(()=>({}));error.textContent=d.error||'接続できませんでした';password.value='';password.focus()}}</script></body></html>""".encode("utf-8")
