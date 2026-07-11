import requests
import pyodbc
import pandas as pd
from datetime import datetime, timedelta
import time

# ===== CONFIG =====
GITHUB_TOKEN = "# Get from: github.com/settings/tokens (Personal Access Token)"
MSSQL_CONN = "Driver={ODBC Driver 18 for SQL Server};Server=#your_server_name;Database=GitHubHealthAnalytics;Trusted_Connection=yes;TrustServerCertificate=yes;Encrypt=no;"

# target repos 
REPOS_TO_FETCH = [
    "pandas-dev/pandas",           # Very active, huge team
    "apache/airflow",              # Active, large team
    "pytorch/pytorch",             # Very active, large team
    "tensorflow/tensorflow",        # Very active, large team
    "kubernetes/kubernetes",        # Very active, large team
    "nodejs/node",                 # Very active, large team
    "python/cpython",              # Very active, large team
    "torvalds/linux",              # REAL repo, massive, active
    "microsoft/vscode",            # REAL repo, very active
    "facebook/react",              # REAL repo, very active
]

# ===== GITHUB API FUNCTIONS =====

def get_github_headers():
    """Set up API headers with token."""
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

def fetch_repo_info(owner, repo_name):
    """Fetch basic repo metadata."""
    url = f"https://api.github.com/repos/{owner}/{repo_name}"
    response = requests.get(url, headers=get_github_headers())
    
    if response.status_code != 200:
        print(f" Failed to fetch {owner}/{repo_name}: {response.status_code}")
        return None
    
    data = response.json()
    
    return {
        "repo_id": data["id"],
        "repo_name": data["name"],
        "owner_name": data["owner"]["login"],
        "full_name": data["full_name"],
        "url": data["html_url"],
        "description": data.get("description", ""),
        "stars": data["stargazers_count"],
        "forks": data["forks_count"],
        "watchers": data["watchers_count"],
        "open_issues": data["open_issues_count"],
        "created_at": data["created_at"],
        "last_updated": data["updated_at"],
        "is_archived": data["archived"],
        "language": data.get("language", "Unknown"),
    }

def fetch_commits(owner, repo_name, days=180):
    """Fetch commits from last N days."""
    since_date = (datetime.utcnow() - timedelta(days=days)).isoformat() + "Z"
    url = f"https://api.github.com/repos/{owner}/{repo_name}/commits?since={since_date}&per_page=100"
    
    commits = []
    page = 1
    
    while page <= 3:  # Limit to first 3 pages (300 commits) to avoid rate limits
        response = requests.get(url + f"&page={page}", headers=get_github_headers())
        
        if response.status_code != 200:
            break
        
        data = response.json()
        if not data:
            break
        
        for commit in data:
            commits.append({
                "commit_id": commit["sha"],
                "repo_id": None,  
                "commit_date": commit["commit"]["author"]["date"],
                "author_name": commit["commit"]["author"]["name"],
                "message": commit["commit"]["message"][:500],  
            })
        
        page += 1
        time.sleep(0.5)  # Rate limiting
    
    return commits

def fetch_issues(owner, repo_name):
    """Fetch open and closed issues."""
    url = f"https://api.github.com/repos/{owner}/{repo_name}/issues?state=all&per_page=100"
    
    issues = []
    page = 1
    
    while page <= 2:  # Limit to first 2 pages
        response = requests.get(url + f"&page={page}", headers=get_github_headers())
        
        if response.status_code != 200:
            break
        
        data = response.json()
        if not data:
            break
        
        for issue in data:
            issues.append({
                "issue_id": issue["id"],
                "repo_id": None,  # Will be filled later
                "issue_title": issue["title"][:500],
                "issue_state": issue["state"],
                "created_at": issue["created_at"],
                "closed_at": issue.get("closed_at"),
            })
        
        page += 1
        time.sleep(0.5)
    
    return issues

def fetch_contributors(owner, repo_name):
    """Fetch top contributors."""
    url = f"https://api.github.com/repos/{owner}/{repo_name}/contributors?per_page=50"
    
    response = requests.get(url, headers=get_github_headers())
    contributors = []
    
    if response.status_code == 200:
        data = response.json()
        for contrib in data:
            contributors.append({
                "repo_id": None,  # Will be filled later
                "contributor_name": contrib["login"],
                "contribution_count": contrib["contributions"],
            })
    
    return contributors

# ===== DATABASE FUNCTIONS =====

def insert_repos(repos_list):
    """Insert repositories into MSSQL."""
    conn =pyodbc.connect(MSSQL_CONN)
    cursor = conn.cursor()
    
    for repo in repos_list:
        try:
            cursor.execute("""
                INSERT INTO Repositories 
                (repo_id, repo_name, owner_name, full_name, url, description, 
                 stars, forks, watchers, open_issues, created_at, last_updated, 
                 is_archived, language)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                repo["repo_id"], repo["repo_name"], repo["owner_name"], 
                repo["full_name"], repo["url"], repo["description"],
                repo["stars"], repo["forks"], repo["watchers"], repo["open_issues"],
                repo["created_at"], repo["last_updated"], repo["is_archived"], 
                repo["language"]
            ))
        except pyodbc.IntegrityError:
            print(f" Repo {repo['full_name']} already exists, skipping...")
    
    conn.commit()
    conn.close()
    print(f" Inserted {len(repos_list)} repositories")

def insert_commits(commits_list, repo_id):
    """Insert commits into MSSQL."""
    conn = pyodbc.connect(MSSQL_CONN)
    cursor = conn.cursor()
    
    for commit in commits_list:
        commit["repo_id"] = repo_id
        try:
            cursor.execute("""
                INSERT INTO Commits 
                (commit_id, repo_id, commit_date, author_name, message)
                VALUES (?, ?, ?, ?, ?)
            """, (
                commit["commit_id"], commit["repo_id"], 
                commit["commit_date"], commit["author_name"], commit["message"]
            ))
        except pyodbc.IntegrityError:
            pass  # Skip duplicates
    
    conn.commit()
    conn.close()
    print(f" Inserted {len(commits_list)} commits for repo_id {repo_id}")

def insert_issues(issues_list, repo_id):
    """Insert issues into MSSQL."""
    conn = pyodbc.connect(MSSQL_CONN)
    cursor = conn.cursor()
    
    for issue in issues_list:
        issue["repo_id"] = repo_id
        try:
            cursor.execute("""
                INSERT INTO Issues 
                (issue_id, repo_id, issue_title, issue_state, created_at, closed_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                issue["issue_id"], issue["repo_id"], issue["issue_title"],
                issue["issue_state"], issue["created_at"], issue["closed_at"]
            ))
        except pyodbc.IntegrityError:
            pass
    
    conn.commit()
    conn.close()
    print(f" Inserted {len(issues_list)} issues for repo_id {repo_id}")

def insert_contributors(contributors_list, repo_id):
    """Insert contributors into MSSQL."""
    conn = pyodbc.connect(MSSQL_CONN)
    cursor = conn.cursor()
    
    for contrib in contributors_list:
        contrib["repo_id"] = repo_id
        cursor.execute("""
            INSERT INTO Contributors 
            (repo_id, contributor_name, contribution_count)
            VALUES (?, ?, ?)
        """, (
            contrib["repo_id"], contrib["contributor_name"], 
            contrib["contribution_count"]
        ))
    
    conn.commit()
    conn.close()
    print(f" Inserted {len(contributors_list)} contributors for repo_id {repo_id}")

# ===== MAIN EXECUTION =====

def main():
    print(" Starting GitHub data fetch...\n")
    
    repos_data = []
    
    # Fetch data for each repo
    for full_name in REPOS_TO_FETCH:
        owner, repo_name = full_name.split("/")
        print(f"📥 Fetching {full_name}...")
        
        # Fetch repo info
        repo_info = fetch_repo_info(owner, repo_name)
        if not repo_info:
            continue
        
        repos_data.append(repo_info)
        repo_id = repo_info["repo_id"]
        
        # Fetch related data
        commits = fetch_commits(owner, repo_name)
        issues = fetch_issues(owner, repo_name)
        contributors = fetch_contributors(owner, repo_name)
        
        print(f"   - {len(commits)} commits found")
        print(f"   - {len(issues)} issues found")
        print(f"   - {len(contributors)} contributors found\n")
        
        time.sleep(1)  # Rate limiting
    
    print("\n Inserting into MSSQL...\n")
    insert_repos(repos_data)

    for full_name in REPOS_TO_FETCH:
        owner, repo_name = full_name.split("/")

        repo = next((r for r in repos_data if r["full_name"] == full_name), None)

        if repo is None:
            print(f"Skipping {full_name}: Repository not found in fetched data.")
            continue

        repo_id = repo["repo_id"]

        commits = fetch_commits(owner, repo_name)
        issues = fetch_issues(owner, repo_name)
        contributors = fetch_contributors(owner, repo_name)

        if commits:
            insert_commits(commits, repo_id)

        if issues:
            insert_issues(issues, repo_id)

        if contributors:
            insert_contributors(contributors, repo_id)
    
    print("\n Data fetch complete!")

if __name__ == "__main__":
    main()