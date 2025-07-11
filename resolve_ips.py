import subprocess
from pathlib import Path
from collections import defaultdict

# === CONFIG ===
DOMAINS = [
    "*.eu-central-1.aws.proxy.prod.fivetran.com",
    "orchestrator.fivetran.com"
]
CURRENT_IPS_FILE = Path("current_ips.txt")
PREVIOUS_IPS_FILE = Path("previous_ips.txt")
DNS_SERVER = "8.8.8.8"  # Public DNS server (Google). Optional — can omit to use system default.

def resolve_with_dig(domain):
    try:
        result = subprocess.run(
            ["dig", "+short", domain, f"@{DNS_SERVER}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        # Filter valid IP addresses (IPv4 only here)
        return sorted([line.strip() for line in result.stdout.splitlines() if line.strip() and line[0].isdigit()])
    except subprocess.TimeoutExpired:
        print(f"Timeout resolving {domain}")
        return []
    except Exception as e:
        print(f"Error resolving {domain}: {e}")
        return []

def save_ips(ip_map, file_path):
    lines = []
    for domain, ips in ip_map.items():
        lines.append(f"# {domain}")
        lines.extend(ips)
    file_path.write_text("\n".join(lines))

def load_ips(file_path):
    ip_map = defaultdict(list)
    if not file_path.exists():
        return ip_map

    current_domain = None
    for line in file_path.read_text().splitlines():
        if line.startswith("# "):
            current_domain = line[2:].strip()
        elif current_domain and line.strip():
            ip_map[current_domain].append(line.strip())
    return ip_map

def main():
    current_ip_map = {}
    for domain in DOMAINS:
        ips = resolve_with_dig(domain)
        current_ip_map[domain] = ips
        print(f"{domain} resolved to: {ips}")

    previous_ip_map = load_ips(PREVIOUS_IPS_FILE)

    changed = False
    for domain in DOMAINS:
        prev = previous_ip_map.get(domain, [])
        curr = current_ip_map.get(domain, [])
        if prev != curr:
            changed = True
            print(f"\n🔁 IPs changed for {domain}")
            print(f"Previous: {prev}")
            print(f"Current:  {curr}")
        else:
            print(f"\n✅ No change for {domain}")

    save_ips(current_ip_map, CURRENT_IPS_FILE)
    save_ips(current_ip_map, PREVIOUS_IPS_FILE)

if __name__ == "__main__":
    main()
