import os
import requests
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- CONFIGURATION ---
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
    ("jellyfin", "jellyfin")
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
            
            # 1. Strip HTML tags to get plain text so regex doesn't get confused
            # This ensures that even if you bold the text inside the brackets, it still works.
            text = re.sub('<[^<]+?>', ' ', html_content)
            
            # 2. Look for the pattern [appname: version]
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
        url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
        response = requests.get(url, headers=gh_headers)

        latest_ver = "N/A"
        rel_date = "N/A"
        rel_url = "#"
        
        if response.status_code == 200:
            data = response.json()
            latest_ver = data.get("tag_name", "N/A")
            rel_date = data.get("published_at", "")[:10]
            rel_url = data.get("html_url", "#")

        # Match against BookStack data
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

def generate_html(releases):
    html_template = """
    <html>
    <head>
        <title>Service Version Dashboard</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f0f2f5; padding: 40px; color: #333; }}
            .container {{ max-width: 1000px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            h1 {{ border-bottom: 2px solid #007bff; padding-bottom: 10px; color: #007bff; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ padding: 15px; text-align: left; border-bottom: 1px solid #eee; }}
            th {{ background-color: #f8f9fa; color: #555; text-transform: uppercase; font-size: 0.85rem; }}
            tr:hover {{ background-color: #fcfcfc; }}
            .status-ok {{ color: #28a745; font-weight: bold; }}
            .status-update {{ background: #fff3cd; color: #856404; font-weight: bold; padding: 4px 8px; border-radius: 4px; }}
            .status-unknown {{ color: #6c757d; font-style: italic; }}
            a {{ color: #007bff; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>System Version Monitor</h1>
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
        f.write(html_template.format(rows=rows))

if __name__ == "__main__":
    print("Fetching data from GitHub and BookStack...")
    data = fetch_data()
    generate_html(data)
    print(f"Dashboard updated: {OUTPUT_FILE}")