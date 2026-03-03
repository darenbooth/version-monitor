# Version Monitor

A lightweight, self-hosted Docker dashboard to track the latest releases of your favorite GitHub repositories. No more manual checking, see what needs updating at a glance. Also make notes on how to check version and how to update in markdown.

## 🚀 Features

* Dark Mode by Default: Easy on the eyes for late-night home labbing.

* Persistent Storage: Uses SQLite to save your watched repos and notes.

* Markdown Support: Keep detailed update notes or "how-to" guides for each service.

* Automatic Fallback: Intelligently checks GitHub Releases and Tags.

* No Dependencies: Doesn't require external databases or complex setups.

## 🛠️ Step 1: Create a GitHub API Token

To prevent being rate-limited, this app requires a GitHub Personal Access Token (PAT).

1. Log in to your GitHub account.

2. Go to Settings > Developer Settings > Personal access tokens > Tokens (classic).

3. Click Generate new token (classic).

4. Give it a name (e.g., "Version Monitor").

5. Select Scopes: You do not need any special permissions for public repos. Just leave everything unchecked.

6. Click Generate token and copy the code immediately.

## 📄 Step 2: Prepare the .env File

1. Create a file named .env in your project folder. This keeps your secrets safe and out of the main configuration. Paste this into .env file.

`GITHUB_TOKEN=your_token_here_starting_with_ghp_`

## 🐳 Step 3: Deploy with Docker Compose

1. Create a docker-compose.yml file in the same directory as your .env file.
```
services:
  version-monitor:
    image: darenbooth/version-monitor:latest
    container_name: version-monitor
    ports:
      - "8136:80"
    env_file:
      - .env
    volumes:
      - ./monitor_data:/app/data
    restart: always
```

2. Launch the service:

`docker compose up -d`

3. Access the dashboard at http://localhost:8136.

## 📝 How to Use

### Adding Repositories

Use the top bar to add the Owner and Repo Name.

* Example: For https://github.com/home-assistant/core, the owner is home-assistant and the repo is core.

### Managing Notes (Markdown)

1. Click the Notes button on any service to expand the management tray.

2. Update Local Version: Manually type in the version you currently have installed.

3. Markdown Notes: You can use standard Markdown to keep track of update commands:

### Status Colors:

* OK (Lime Green): Your version matches GitHub.

* UPDATE (Yellow): A newer version is available on GitHub.

* UNKNOWN (Grey): No local version has been set yet.

### 🔧 Management Commands

* View Logs: `docker compose logs -f`

* Restart: `docker compose restart`

* Update to Newest Version:

```
docker compose pull
docker compose up -d
```
