import os
import requests
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- CONFIGURATION ---
DASHBOARD_VERSION = "v0.5"  # Update this when pushing new images
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
BOOKSTACK_URL = os.getenv("BOOKSTACK_URL", "").rstrip('/')
BS_ID = os.getenv("BOOKSTACK_TOKEN_ID")
BS_SECRET = os.getenv("BOOKSTACK_TOKEN_SECRET")
BS_PAGE_ID = os.getenv("BOOKSTACK_PAGE_ID")

WATCHED_REPOS = [
    ("home-assistant", "operating-system"),
    ("home-assistant", "core"),
    ("filebrowser", "filebrowser"),
    ("immich-app", "immich"),
    ("jellyfin", "jellyfin"),
    ("open-webui", "open-webui"),
    ("dani-garcia", "vaultwarden"),
    ("BookStackApp", "BookStack"),
    ("qdm12", "ddns-updater"),
    ("nginx", "nginx"),
    ("NginxProxyManager", "nginx-proxy-manager"),
    ("wizarrrr", "wizarr"),
    ("qbittorrent", "qBittorrent"),
    ("Prowlarr", "Prowlarr"),
    ("Sonarr", "Sonarr"),
    ("Radarr", "Radarr"),
    ("Lidarr", "Lidarr"),
    ("drakkan", "sftpgo"),
    ("tailscale", "tailscale"),
    ("darenbooth", "sc_commodity_manager"),
    ("darenbooth", "version_manager")
]
OUTPUT_FILE = "/var/www/html/index.html"

# Validation
if not GITHUB_TOKEN:
    print("Error: GITHUB_TOKEN not found.")
    exit(1)

def get_current_versions_from_bookstack():
    """Fetches and parses the BookStack page for current versions using [app:ver] markers."""
    if not all([BOOKSTACK_URL, BS_ID, BS_SECRET, BS_PAGE_ID]):
        print("BookStack configuration missing. Skipping current version check.")
        return {}

    url = f"{BOOKSTACK_URL}/api/pages/{BS_PAGE_ID}"
    headers = {
        "Authorization": f"Token {BS_ID}:{BS_SECRET}",
        "Accept": "application/json",
        "User-Agent": "VersionDashboard-App"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            html_content = response.json().get('html', '')
            versions = {}
            
            # Strip HTML tags
            text = re.sub('<[^<]+?>', ' ', html_content)
            
            # Look for [appname: version]
            matches = re.findall(r'\[(.*?)\]', text)
            
            for match in matches:
                if ':' in match:
                    parts = match.split(':', 1)
                    app_name = parts[0].strip().lower()
                    version_val = parts[1].strip()
                    versions[app_name] = version_val
            
            return versions
        else:
            print(f"BookStack API Error: {response.status_code}")
            return {}
    except Exception as e:
        print(f"Failed to connect to BookStack: {e}")
        return {}

def get_latest_github_info(owner, repo, headers):
    """Fetches latest version, falling back to tags if no formal release exists."""
    release_url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    try:
        response = requests.get(release_url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                "version": data.get("tag_name", "N/A"),
                "date": data.get("published_at", "")[:10],
                "url": data.get("html_url", "#")
            }
        
        # Fallback to Tags API
        elif response.status_code == 404:
            tags_url = f"https://api.github.com/repos/{owner}/{repo}/tags"
            tags_response = requests.get(tags_url, headers=headers, timeout=10)
            if tags_response.status_code == 200:
                tags_data = tags_response.json()
                if tags_data:
                    tag_name = tags_data[0].get('name', 'N/A')
                    return {
                        "version": tag_name,
                        "date": "Tag (Recent)", 
                        "url": f"https://github.com/{owner}/{repo}/tags"
                    }
        
        return {"version": "N/A", "date": "N/A", "url": "#"}
    except Exception as e:
        print(f"Request error for {repo}: {e}")
        return {"version": "Error", "date": "Error", "url": "#"}

def fetch_data():
    """Gathers data from GitHub and compares it with BookStack."""
    current_vers = get_current_versions_from_bookstack()
    results = []
    
    gh_headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "VersionDashboard-App"
    }

    for owner, repo in WATCHED_REPOS:
        info = get_latest_github_info(owner, repo, gh_headers)
        
        latest_ver = info["version"]
        rel_date = info["date"]
        rel_url = info["url"]

        # Exact match only
        my_version = current_vers.get(repo.lower(), "Unknown")
        
        # Determine status
        if my_version == "Unknown":
            status_class = "status-unknown"
            status_text = "Not Documented"
        elif latest_ver == my_version:
            status_class = "status-ok"
            status_text = "Up to Date"
        else:
            status_class = "status-update"
            status_text = "Update Available"

        results.append({
            "name": repo,
            "latest": latest_ver,
            "current": my_version,
            "date": rel_date,
            "url": rel_url,
            "status_class": status_class,
            "status_text": status_text
        })
    
    return results

def generate_html(releases, app_version):
    html_template = """
    <html>
    <head>
        <title>Version Monitor {app_version}</title>
        <style>
            /* DARK MODE THEME */
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #121212; padding: 40px; color: #e0e0e0; }}
            .container {{ max-width: 1000px; margin: auto; background: #1e1e1e; padding: 20px; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }}
            h1 {{ border-bottom: 2px solid #3a86ff; padding-bottom: 10px; color: #3a86ff; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ padding: 15px; text-align: left; border-bottom: 1px solid #333; }}
            th {{ background-color: #2a2a2a; color: #b0b0b0; text-transform: uppercase; font-size: 0.85rem; }}
            tr:hover {{ background-color: #252525; }}
            
            .status-ok {{ color: #28a745; font-weight: bold; }}
            .status-update {{ background: rgba(255, 193, 7, 0.15); color: #ffc107; font-weight: bold; padding: 4px 8px; border-radius: 4px; }}
            .status-unknown {{ color: #a0a0a0; font-style: italic; }}
            
            a {{ color: #3a86ff; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
            code {{ background: #2a2a2a; color: #e0e0e0; padding: 2px 5px; border-radius: 3px; font-family: monospace; border: 1px solid #333; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Version Monitor {app_version}</h1>
            <table>
                <tr>
                    <th>Service</th>
                    <th>Current (BookStack)</th>
                    <th>Latest (GitHub)</th>
                    <th>Release Date</th>
                    <th>Status</th>
                </tr>
                {rows}
            </table>
        </div>
    </body>
    </html>
    """

    rows = ""
    for r in releases:
        rows += f"""
        <tr>
            <td><a href="{r['url']}" target="_blank">{r['name']}</a></td>
            <td><code>{r['current']}</code></td>
            <td><code>{r['latest']}</code></td>
            <td>{r['date']}</td>
            <td><span class="{r['status_class']}">{r['status_text']}</span></td>
        </tr>
        """

    with open(OUTPUT_FILE, "w") as f:
        f.write(html_template.format(app_version=app_version, rows=rows))

if __name__ == "__main__":
    print(f"Fetching data from GitHub and BookStack for {DASHBOARD_VERSION}...")
    data = fetch_data()
    generate_html(data, DASHBOARD_VERSION)
    print(f"Dashboard updated: {OUTPUT_FILE}")