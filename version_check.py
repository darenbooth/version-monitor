import os
import requests
import sqlite3
import markdown
from flask import Flask, render_template_string, request, redirect

app = Flask(__name__)
# Database must live in the volume-mapped folder
DB_PATH = "/app/data/monitor.db"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
DASHBOARD_VERSION = "v1.1"

# --- DATABASE SETUP ---
def init_db():
    """Initializes the SQLite database and injects the default system repo."""
    if not os.path.exists("/app/data"):
        os.makedirs("/app/data")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Create the table
    c.execute('''CREATE TABLE IF NOT EXISTS repos 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, owner TEXT, repo TEXT, current_ver TEXT, notes TEXT)''')
    
    # Check if the system repo exists, if not, add it with your custom note
    c.execute("SELECT count(*) FROM repos WHERE repo = 'version-monitor'")
    if c.fetchone()[0] == 0:
        default_note = "## To Find Version:\r\n\r\nThe version is proudly displayed at the top of the page.\r\n\r\n## To Update:\r\n\r\n`cd path/to/directory`\r\n\r\n`docker compose pull && docker compose up -d`\r\n\r\n## Donation:\r\n\r\nIf you find this container useful, please consider donating a couple of dollars to me here\r\n\r\n<https://www.paypal.com/donate/?hosted_button_id=3TL69W8RM7CYEI>"
        c.execute("INSERT INTO repos (owner, repo, current_ver, notes) VALUES (?, ?, ?, ?)",
                  ("darenbooth", "version-monitor", DASHBOARD_VERSION, default_note))
    conn.commit()
    conn.close()

def get_latest_github_info(owner, repo):
    """Fetches the latest version from GitHub API."""
    if not GITHUB_TOKEN:
        return "Missing Token", "N/A"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    try:
        # 1. Try Releases
        r = requests.get(f"https://api.github.com/repos/{owner}/{repo}/releases/latest", headers=headers, timeout=5)
        if r.status_code == 200:
            data = r.json()
            return data.get("tag_name", "N/A"), data.get("published_at", "")[:10]
        # 2. Fallback to Tags
        elif r.status_code == 404:
            tags_r = requests.get(f"https://api.github.com/repos/{owner}/{repo}/tags", headers=headers, timeout=5)
            if tags_r.status_code == 200 and tags_r.json():
                return tags_r.json()[0].get('name', 'N/A'), "Tag (Recent)"
    except:
        pass
    return "N/A", "N/A"

# --- ROUTES ---
@app.route('/')
def index():
    """Main dashboard view."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Sort to keep the system repo at the very top
    c.execute("SELECT * FROM repos ORDER BY (repo = 'version-monitor') DESC, repo ASC")
    rows = c.fetchall()
    
    services = []
    for row in rows:
        rid, owner, repo, current, notes = row
        latest, date = get_latest_github_info(owner, repo)
        
        # Check if this is the system repo
        is_system = (repo == "version-monitor" and owner == "darenbooth")
        
        # Force the system repo to show the hardcoded DASHBOARD_VERSION
        display_current = DASHBOARD_VERSION if is_system else (current or "Unknown")
        
        status = "update"
        if latest == "N/A": status = "unknown"
        elif display_current == latest: status = "ok"

        services.append({
            "id": rid, "owner": owner, "name": repo, "current": display_current,
            "latest": latest, "date": date, "notes": markdown.markdown(notes or ""),
            "raw_notes": notes or "", "status": status, "is_system": is_system
        })
    conn.close()
    return render_template_string(HTML_TEMPLATE, services=services, version=DASHBOARD_VERSION)

@app.route('/add', methods=['POST'])
def add():
    owner = request.form['owner'].strip()
    repo = request.form['repo'].strip()
    current = request.form['current'].strip()
    if owner and repo:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO repos (owner, repo, current_ver, notes) VALUES (?, ?, ?, '')", (owner, repo, current))
        conn.commit()
        conn.close()
    return redirect('/')

@app.route('/update_notes', methods=['POST'])
def update_notes():
    rid = request.form['id']
    notes = request.form['notes'].strip()
    conn = sqlite3.connect(DB_PATH)
    # Check if a 'current' version was actually sent (it's hidden for system repo)
    if 'current' in request.form:
        conn.execute("UPDATE repos SET notes = ?, current_ver = ? WHERE id = ?", (notes, request.form['current'], rid))
    else:
        conn.execute("UPDATE repos SET notes = ? WHERE id = ?", (notes, rid))
    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/delete/<int:repo_id>', methods=['POST'])
def delete(repo_id):
    conn = sqlite3.connect(DB_PATH)
    # Security: Prevent deletion of the system repo
    conn.execute("DELETE FROM repos WHERE id = ? AND repo != 'version_manager'", (repo_id,))
    conn.commit()
    conn.close()
    return redirect('/')

# --- FULL HTML TEMPLATE ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Version Monitor {{ version }}</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #121212; color: #e0e0e0; padding: 20px; }
        .container { max-width: 1000px; margin: auto; background: #1e1e1e; padding: 20px; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }
        h1 { border-bottom: 2px solid #32CD32; padding-bottom: 10px; color: #32CD32; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 12px; border-bottom: 1px solid #333; text-align: left; }
        th { background-color: #2a2a2a; color: #b0b0b0; text-transform: uppercase; font-size: 0.85rem; }
        tr:hover { background-color: #252525; }
        .status-ok { color: #32CD32; font-weight: bold; }
        .status-update { color: #ffc107; font-weight: bold; }
        .status-unknown { color: #888; font-style: italic; }
        input, textarea { background: #2a2a2a; color: #e0e0e0; border: 1px solid #444; padding: 8px; border-radius: 4px; width: 100%; box-sizing: border-box; }
        .btn { background: #3a86ff; color: white; border: none; padding: 8px 12px; cursor: pointer; border-radius: 4px; }
        .btn:hover { background: #0056b3; }
        .btn-delete { background: #dc3545; }
        .btn-delete:hover { background: #a71d2a; }
        .notes-row { display: none; background: #252525; }
        .notes-row td { white-space: normal; padding: 20px; }
        .markdown-body { font-size: 0.9em; color: #b0b0b0; line-height: 1.6; }
        .markdown-body code { background: #333; padding: 2px 4px; border-radius: 3px; font-family: monospace; }
        .markdown-body p { margin: 8px 0; }
    </style>
    <script>
        function toggleNotes(id) {
            var x = document.getElementById("notes-" + id);
            x.style.display = (x.style.display === "none") ? "table-row" : "none";
        }
    </script>
</head>
<body>
    <div class="container">
        <h1>Version Monitor {{ version }}</h1>
        
        <form action="/add" method="post" style="margin-bottom: 20px; display: flex; gap: 10px;">
            <input type="text" name="owner" placeholder="Owner (e.g. home-assistant)" required>
            <input type="text" name="repo" placeholder="Repo Name (e.g. core)" required>
            <input type="text" name="current" placeholder="Current Version">
            <button type="submit" class="btn">Add Repo</button>
        </form>

        <table>
            <thead>
                <tr>
                    <th>Service</th>
                    <th>Current</th>
                    <th>Latest</th>
                    <th>Release Date</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                {% for s in services %}
                <tr>
                    <td>{{ s.owner }}/{{ s.name }}</td>
                    <td><code>{{ s.current }}</code></td>
                    <td><code>{{ s.latest }}</code></td>
                    <td>{{ s.date }}</td>
                    <td class="status-{{ s.status }}">
                        {{ s.status.upper() }}
                        <button class="btn" onclick="toggleNotes('{{ s.id }}')" style="padding: 2px 6px; font-size: 0.8em; margin-left: 10px;">Notes</button>
                    </td>
                </tr>
                <tr id="notes-{{ s.id }}" class="notes-row">
                    <td colspan="5">
                        <div style="display:flex; gap: 30px;">
                            <div style="flex:1;">
                                <strong>Preview:</strong><br><br>
                                <div class="markdown-body">{{ s.notes|safe }}</div>
                            </div>
                            
                            <form action="/update_notes" method="post" style="flex:1; display: flex; flex-direction: column; gap: 10px;">
                                <input type="hidden" name="id" value="{{ s.id }}">
                                {% if not s.is_system %}
                                    <label>Current Version:</label>
                                    <input type="text" name="current" value="{{ s.current }}">
                                {% else %}
                                    <p style="font-size: 0.85em; color: #32CD32;">✔ System Managed Version</p>
                                {% endif %}
                                <label>Notes (Markdown):</label>
                                <textarea name="notes" rows="6">{{ s.raw_notes }}</textarea>
                                <button type="submit" class="btn">Save Changes</button>
                            </form>
                            
                            {% if not s.is_system %}
                            <form action="/delete/{{ s.id }}" method="post" onsubmit="return confirm('Delete this repository?');">
                                <button type="submit" class="btn btn-delete">DELETE</button>
                            </form>
                            {% endif %}
                        </div>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</body>
</html>
"""

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=80)