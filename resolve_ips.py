import subprocess
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# === CONFIG ===
DOMAINS = [
    "eu-central-1.aws.proxy.prod.fivetran.com",
    "orchestrator.fivetran.com"
]
CURRENT_IPS_FILE = Path("current_ips.txt")
PREVIOUS_IPS_FILE = Path("previous_ips.txt")
REPORT_FILE = Path("ip_change_report.txt")
DNS_SERVER = "8.8.8.8"  # Change if needed

def resolve_with_dig(domain):
    try:
        result = subprocess.run(
            ["dig", "+short", domain, f"@{DNS_SERVER}"],
            capture_output=True,
            text=True,
            timeout=5
        )
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

def generate_change_report(prev_map, curr_map):
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    lines = [f"=== IP Change Check at {timestamp} ==="]
    changes_found = False

    for domain in DOMAINS:
        prev_ips = set(prev_map.get(domain, []))
        curr_ips = set(curr_map.get(domain, []))
        added = curr_ips - prev_ips
        removed = prev_ips - curr_ips

        if added or removed:
            changes_found = True
            lines.append(f"\n## {domain}")
            if added:
                lines.append("Added:")
                lines.extend([f"+ {ip}" for ip in sorted(added)])
            if removed:
                lines.append("Removed:")
                lines.extend([f"- {ip}" for ip in sorted(removed)])

    if not changes_found:
        lines.append("No IP changes detected.")

    lines.append("\n")
    with REPORT_FILE.open("a") as f:
        f.write("\n".join(lines))

def main():
    current_ip_map = {domain: resolve_with_dig(domain) for domain in DOMAINS}
    previous_ip_map = load_ips(PREVIOUS_IPS_FILE)

    for domain in DOMAINS:
        print(f"{domain} resolved to: {current_ip_map[domain]}")

    generate_change_report(previous_ip_map, current_ip_map)
    save_ips(current_ip_map, CURRENT_IPS_FILE)
    save_ips(current_ip_map, PREVIOUS_IPS_FILE)

if __name__ == "__main__":
    main()
