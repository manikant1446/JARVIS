"""
actions/cybersec_tools.py — Defensive cybersecurity reconnaissance, diagnostics, and security audits for MARK LIII.
Supports: WHOIS, DNS, IP/ISP intelligence, port scanning, ping, traceroute, HTTP status, TLS certificates,
local listening ports, suspicious connections, security audit, and defensive stress resilience tests.
"""
from __future__ import annotations

import concurrent.futures
import json
import platform
import socket
import ssl
import subprocess
import time
import urllib.error
import urllib.request
import psutil
from core.permissions import PermissionLevel, execute_with_permission

_OS = platform.system()


def whois_lookup(parameters: dict = None, **kwargs) -> str:
    """Performs a WHOIS query on a domain or IP."""
    domain = (parameters or {}).get("domain", "").strip()
    if not domain:
        return "Please specify a domain name or IP for the WHOIS query."

    domain = domain.replace("https://", "").replace("http://", "").split("/")[0]

    try:
        res = subprocess.run(["whois", domain], capture_output=True, text=True, timeout=12)
        out = res.stdout.strip()
        if not out:
            return f"No WHOIS information found for '{domain}'."

        lines = [line for line in out.splitlines() if not line.startswith("%") and ":" in line]
        summary = lines[:20]
        return f"🔍 WHOIS for {domain}:\n" + "\n".join(summary)
    except Exception as e:
        return f"WHOIS query failed: {e}"


def dns_lookup(parameters: dict = None, **kwargs) -> str:
    """Look up DNS records for a domain (A, MX, NS, TXT)."""
    domain = (parameters or {}).get("domain", "").strip()
    if not domain:
        return "Please specify a domain for DNS lookup."

    domain = domain.replace("https://", "").replace("http://", "").split("/")[0]

    results = [f"🌐 DNS Records for {domain}:"]
    for record_type in ["A", "MX", "NS", "TXT"]:
        try:
            res = subprocess.run(
                ["dig", "+short", domain, record_type],
                capture_output=True, text=True, timeout=6
            )
            out = res.stdout.strip()
            if out:
                results.append(f"\n[{record_type} Records]:\n{out}")
        except Exception:
            pass

    return "\n".join(results) if len(results) > 1 else f"No DNS records resolved for {domain}."


def ip_info(parameters: dict = None, **kwargs) -> str:
    """Get geolocation and ISP information for an IP address or domain."""
    target = (parameters or {}).get("target", "").strip()
    target = target.replace("https://", "").replace("http://", "").split("/")[0]

    try:
        url = f"http://ip-api.com/json/{target}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        if data.get("status") == "fail":
            return f"IP lookup failed: {data.get('message', 'Invalid target')}"

        return (
            f"📍 IP Intelligence — {data.get('query')}:\n"
            f"• Country: {data.get('country')} ({data.get('countryCode')})\n"
            f"• Region/City: {data.get('regionName')}, {data.get('city')}\n"
            f"• ISP / Org: {data.get('isp')} / {data.get('org')}\n"
            f"• AS: {data.get('as')}\n"
            f"• Coordinates: Lat {data.get('lat')}, Lon {data.get('lon')}\n"
            f"• Timezone: {data.get('timezone')}"
        )
    except Exception as e:
        return f"IP information query failed: {e}"


def port_scan(parameters: dict = None, **kwargs) -> str:
    """Scans common TCP ports on a given target IP or domain."""
    target = (parameters or {}).get("target", "").strip()
    if not target:
        return "Please specify a target IP or domain."

    target = target.replace("https://", "").replace("http://", "").split("/")[0]

    common_ports = {
        21: "FTP", 22: "SSH", 25: "SMTP", 53: "DNS", 80: "HTTP",
        110: "POP3", 143: "IMAP", 443: "HTTPS", 3306: "MySQL",
        3389: "RDP", 5432: "PostgreSQL", 8080: "HTTP-Alt",
    }

    open_ports = []
    try:
        ip = socket.gethostbyname(target)
    except Exception as e:
        return f"Could not resolve target '{target}': {e}"

    for port, service in common_ports.items():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.6)
        result = sock.connect_ex((ip, port))
        if result == 0:
            open_ports.append(f"• Port {port} ({service}) — OPEN")
        sock.close()

    if open_ports:
        return f"🛡️ Port Scan Results for {target} ({ip}):\n" + "\n".join(open_ports)
    return f"Port scan completed for {target} ({ip}). None of the top common ports were found open."


def ping_host(parameters: dict = None, **kwargs) -> str:
    """Pings a target host to check packet loss and response latency."""
    target = (parameters or {}).get("target", "").strip()
    if not target:
        return "Please specify a host to ping."

    target = target.replace("https://", "").replace("http://", "").split("/")[0]

    try:
        res = subprocess.run(
            ["ping", "-c", "3", target],
            capture_output=True, text=True, timeout=8
        )
        out = res.stdout.strip()
        return f"📶 Ping results for {target}:\n{out}" if out else "Ping request received no response."
    except Exception as e:
        return f"Ping failed: {e}"


def traceroute(parameters: dict = None, **kwargs) -> str:
    """Traces network hops to a destination host."""
    target = (parameters or {}).get("target", "").strip()
    if not target:
        return "Please specify a destination host."

    target = target.replace("https://", "").replace("http://", "").split("/")[0]

    try:
        res = subprocess.run(
            ["traceroute", "-m", "15", "-w", "1", target],
            capture_output=True, text=True, timeout=18
        )
        out = res.stdout.strip()
        return f"🛤️ Traceroute to {target}:\n{out[:2000]}" if out else "Traceroute returned no hops."
    except Exception as e:
        return f"Traceroute failed: {e}"


def http_status_check(parameters: dict = None, **kwargs) -> str:
    """Checks the HTTP status code, latency, and response headers for a URL."""
    url = (parameters or {}).get("url", "").strip()
    if not url:
        return "Please specify a URL to inspect."
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    try:
        t0 = time.time()
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (MARK-LIII-Auditor)"})
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            elapsed = int((time.time() - t0) * 1000)
            status = resp.status
            reason = resp.reason
            server = resp.headers.get("Server", "Unknown")
            return (
                f"🌐 HTTP Status for {url}:\n"
                f"• Status Code: {status} ({reason})\n"
                f"• Latency: {elapsed}ms\n"
                f"• Server: {server}\n"
                f"• Content-Type: {resp.headers.get('Content-Type', 'Unknown')}"
            )
    except urllib.error.HTTPError as e:
        return f"🌐 HTTP Error for {url}: Status {e.code} ({e.reason})"
    except Exception as e:
        return f"HTTP check failed: {e}"


def tls_certificate_info(parameters: dict = None, **kwargs) -> str:
    """Inspects the SSL/TLS certificate, expiration, and issuer for a domain."""
    domain = (parameters or {}).get("domain", "").strip()
    if not domain:
        return "Please specify a domain name."
    domain = domain.replace("https://", "").replace("http://", "").split("/")[0]

    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=6) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                issuer = dict(x[0] for x in cert.get("issuer", []))
                subject = dict(x[0] for x in cert.get("subject", []))
                not_before = cert.get("notBefore")
                not_after = cert.get("notAfter")
                return (
                    f"🔒 TLS/SSL Certificate for {domain}:\n"
                    f"• Common Name: {subject.get('commonName', domain)}\n"
                    f"• Issuer: {issuer.get('organizationName', issuer.get('commonName', 'Unknown'))}\n"
                    f"• Valid From: {not_before}\n"
                    f"• Expires: {not_after}\n"
                    f"• Protocol Version: {ssock.version()}\n"
                    f"• Cipher Suite: {ssock.cipher()[0]}"
                )
    except Exception as e:
        return f"Could not retrieve TLS certificate for {domain}: {e}"


def local_port_inspection(parameters: dict = None, **kwargs) -> str:
    """Inspects all active listening ports and processes on the local machine."""
    try:
        listening = []
        for conn in psutil.net_connections(kind='inet'):
            if conn.status == 'LISTEN':
                port = conn.laddr.port
                pid = conn.pid
                pname = "Unknown"
                if pid:
                    try:
                        pname = psutil.Process(pid).name()
                    except Exception:
                        pass
                listening.append(f"• Port {port} (PID {pid}: {pname})")
        listening = sorted(list(set(listening)))
        if listening:
            return f"🔌 Local Listening Ports ({len(listening)} services):\n" + "\n".join(listening[:30])
        return "No active TCP listening ports found."
    except Exception as e:
        try:
            res = subprocess.run(["lsof", "-iTCP", "-sTCP:LISTEN", "-P", "-n"], capture_output=True, text=True, timeout=5)
            lines = res.stdout.strip().splitlines()
            return f"🔌 Local Listening Ports:\n" + "\n".join(lines[:25])
        except Exception as e2:
            return f"Local port inspection failed: {e}"


def suspicious_connection_inspection(parameters: dict = None, **kwargs) -> str:
    """Inspects active external network connections for unusual ports or suspicious endpoints."""
    try:
        flagged = []
        conns = psutil.net_connections(kind='inet')
        for conn in conns:
            if conn.status == 'ESTABLISHED' and conn.raddr:
                r_ip, r_port = conn.raddr.ip, conn.raddr.port
                if r_ip.startswith("127.") or r_ip.startswith("192.168.") or r_ip.startswith("10."):
                    continue
                if r_port not in (80, 443, 8080, 8443, 22, 53, 5223, 5228):
                    pname = "Unknown"
                    if conn.pid:
                        try:
                            pname = psutil.Process(conn.pid).name()
                        except Exception:
                            pass
                    flagged.append(f"⚠️ {pname} (PID {conn.pid}) connected to {r_ip}:{r_port}")
        if flagged:
            return f"🔍 Flagged External Connections ({len(flagged)}):\n" + "\n".join(flagged[:15])
        return "✅ Network Connection Inspection: All current connections are using standard trusted ports (HTTP/HTTPS/DNS/SSH)."
    except Exception as e:
        return f"Connection inspection failed: {e}"


def basic_security_audit(parameters: dict = None, **kwargs) -> str:
    """Performs a local macOS security audit (Firewall, FileVault, SIP, Gatekeeper)."""
    if _OS != "Darwin":
        return "macOS basic security audit is only supported on macOS."

    checks = []
    # Firewall
    try:
        res = subprocess.run(["/usr/libexec/ApplicationFirewall/socketfilterfw", "--getglobalstate"], capture_output=True, text=True, timeout=3)
        fw = "Enabled" if "enabled" in res.stdout.lower() else "Disabled"
        checks.append(f"• Application Firewall: {fw}")
    except Exception:
        checks.append("• Application Firewall: Unknown")

    # FileVault
    try:
        res = subprocess.run(["fdesetup", "status"], capture_output=True, text=True, timeout=3)
        fv = "On (Encrypted)" if "on" in res.stdout.lower() else "Off"
        checks.append(f"• FileVault Disk Encryption: {fv}")
    except Exception:
        checks.append("• FileVault: Unknown")

    # SIP
    try:
        res = subprocess.run(["csrutil", "status"], capture_output=True, text=True, timeout=3)
        sip = "Enabled" if "enabled" in res.stdout.lower() else "Disabled"
        checks.append(f"• System Integrity Protection (SIP): {sip}")
    except Exception:
        checks.append("• SIP: Unknown")

    # Gatekeeper
    try:
        res = subprocess.run(["spctl", "--status"], capture_output=True, text=True, timeout=3)
        gk = "Active" if "assessments enabled" in res.stdout.lower() else "Inactive"
        checks.append(f"• Gatekeeper: {gk}")
    except Exception:
        checks.append("• Gatekeeper: Unknown")

    return "🛡️ macOS Security Audit:\n" + "\n".join(checks)


def defensive_ddos_simulation(parameters: dict = None, **kwargs) -> str:
    """Defensive stress and strength resilience test to check website capacity under load."""
    target = (parameters or {}).get("target", "").strip()
    if not target:
        return "Please specify target website URL or IP to test resilience."

    def _do_stress() -> str:
        url = target if target.startswith("http") else "https://" + target
        burst_count = 30
        successes = 0
        failures = 0
        latencies = []

        def _fetch():
            try:
                t0 = time.time()
                req = urllib.request.Request(url, headers={"User-Agent": "MARK-LIII-StressTest/1.0"})
                ctx = ssl.create_default_context()
                with urllib.request.urlopen(req, context=ctx, timeout=4) as r:
                    lat = int((time.time() - t0) * 1000)
                    return True, lat
            except Exception:
                return False, 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futs = [executor.submit(_fetch) for _ in range(burst_count)]
            for f in concurrent.futures.as_completed(futs):
                ok, lat = f.result()
                if ok:
                    successes += 1
                    latencies.append(lat)
                else:
                    failures += 1

        avg_lat = int(sum(latencies) / len(latencies)) if latencies else 0
        verdict = "Strong & Resilient" if successes >= burst_count * 0.8 else "Degraded or Rate-Limited"
        return (
            f"⚡ Defensive Resilience Test for {url}:\n"
            f"• Burst Requests Sent: {burst_count}\n"
            f"• Successful Responses: {successes}/{burst_count}\n"
            f"• Failed / Throttled: {failures}/{burst_count}\n"
            f"• Average Latency: {avg_lat}ms\n"
            f"• Assessment: {verdict}"
        )

    return execute_with_permission(
        level=PermissionLevel.LEVEL_3_DESTRUCTIVE,
        title=f"Stress test resilience of {target}",
        detail=f"Target: {target}\nDefensive burst test: 30 parallel requests to measure load capacity.",
        action_fn=_do_stress
    )


# ── Multi-tool declarations (auto-discovered by core/action_loader.py) ───────
TOOLS = [
    {
        "name": "whois_lookup",
        "description": "Performs a WHOIS lookup on a domain name or IP to find registration and registrar details.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "domain": {
                    "type": "STRING",
                    "description": "Domain name or IP address (e.g. google.com, github.com)."
                }
            },
            "required": ["domain"]
        },
        "handler": whois_lookup,
    },
    {
        "name": "dns_lookup",
        "description": "Queries DNS records (A, MX, NS, TXT) for a given domain name.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "domain": {
                    "type": "STRING",
                    "description": "Domain name to resolve."
                }
            },
            "required": ["domain"]
        },
        "handler": dns_lookup,
    },
    {
        "name": "ip_info",
        "description": "Fetches IP intelligence: country, city, ISP, organization, and geolocation coordinates.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "target": {
                    "type": "STRING",
                    "description": "Target IP address or domain (leave empty for your own public IP)."
                }
            },
            "required": []
        },
        "handler": ip_info,
    },
    {
        "name": "port_scan",
        "description": "Scans common network service ports (SSH, HTTP, HTTPS, DB, RDP) on an IP or domain.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "target": {
                    "type": "STRING",
                    "description": "Target domain or IP address."
                }
            },
            "required": ["target"]
        },
        "handler": port_scan,
    },
    {
        "name": "ping_host",
        "description": "Sends ICMP echo packets to test network connectivity and latency to a remote server.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "target": {
                    "type": "STRING",
                    "description": "Host name or IP to ping."
                }
            },
            "required": ["target"]
        },
        "handler": ping_host,
    },
    {
        "name": "traceroute",
        "description": "Traces network routing path and intermediate hops to a destination host.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "target": {
                    "type": "STRING",
                    "description": "Target domain or IP to trace."
                }
            },
            "required": ["target"]
        },
        "handler": traceroute,
    },
    {
        "name": "http_status_check",
        "description": "Inspects HTTP status code, latency, server headers, and availability for a web service.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "url": {
                    "type": "STRING",
                    "description": "Website URL to check."
                }
            },
            "required": ["url"]
        },
        "handler": http_status_check,
    },
    {
        "name": "tls_certificate_info",
        "description": "Checks SSL/TLS certificate expiry, issuer, cipher suite, and validity for a domain.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "domain": {
                    "type": "STRING",
                    "description": "Domain name to inspect certificate for."
                }
            },
            "required": ["domain"]
        },
        "handler": tls_certificate_info,
    },
    {
        "name": "local_port_inspection",
        "description": "Lists all active listening TCP ports and associated services running on this machine.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        },
        "handler": local_port_inspection,
    },
    {
        "name": "suspicious_connection_inspection",
        "description": "Audits active outgoing connections to inspect unexpected ports or potential anomalies.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        },
        "handler": suspicious_connection_inspection,
    },
    {
        "name": "basic_security_audit",
        "description": "Audits local macOS security settings including Firewall, FileVault encryption, SIP, and Gatekeeper.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        },
        "handler": basic_security_audit,
    },
    {
        "name": "defensive_ddos_simulation",
        "description": "Performs a defensive resilience stress test (burst requests) to assess website strength and rate limiting. Requires confirmation.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "target": {
                    "type": "STRING",
                    "description": "Domain or URL of the website to test."
                }
            },
            "required": ["target"]
        },
        "handler": defensive_ddos_simulation,
    }
]
