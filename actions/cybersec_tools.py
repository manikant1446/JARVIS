"""
actions/cybersec_tools.py — Cybersecurity reconnaissance, diagnostics, and security knowledge ported from Layra.
Supports: WHOIS lookups, DNS resolution, IP intelligence, port scanning, ping, traceroute, and security guides.
"""
from __future__ import annotations

import json
import socket
import subprocess
import urllib.request


def whois_lookup(parameters: dict = None, **kwargs) -> str:
    """Performs a WHOIS query on a domain or IP."""
    domain = (parameters or {}).get("domain", "").strip()
    if not domain:
        return "Please specify a domain name or IP for the WHOIS query."

    # Remove protocol if user included it
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
    # Dig commands
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
    if not target:
        target = ""  # IP-API returns caller's IP when path is empty

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
        21: "FTP",
        22: "SSH",
        25: "SMTP",
        53: "DNS",
        80: "HTTP",
        110: "POP3",
        143: "IMAP",
        443: "HTTPS",
        3306: "MySQL",
        3389: "RDP",
        5432: "PostgreSQL",
        8080: "HTTP-Alt",
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
    }
]
