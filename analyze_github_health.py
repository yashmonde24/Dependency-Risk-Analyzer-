import pandas as pd
import pyodbc
import numpy as np
from datetime import datetime, timedelta
import json

#  CONFIG 
MSSQL_CONN = "Driver={ODBC Driver 18 for SQL Server};Server=DESKTOP-EUH7TII;Database=GitHubHealthAnalytics;Trusted_Connection=yes;TrustServerCertificate=yes;Encrypt=no;"

#  DATABASE FUNCTIONS 

def query_database(sql_query):
    """Execute SQL query and return DataFrame."""
    conn = pyodbc.connect(MSSQL_CONN)
    df = pd.read_sql(sql_query, conn)
    conn.close()
    return df

# def insert_health_scores(health_df):
#     """Store calculated health scores back into database."""
#     conn = pyodbc.connect(MSSQL_CONN)
#     cursor = conn.cursor()
    
#     # Create table if not exists
#     cursor.execute("""
#         IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'HealthScores')
#         CREATE TABLE HealthScores (
#             repo_id BIGINT PRIMARY KEY,
#             activity_score INT,
#             contributor_score INT,
#             responsiveness_score INT,
#             stability_score INT,
#             overall_health_score INT,
#             health_status NVARCHAR(50),
#             calculated_date DATETIME DEFAULT GETDATE(),
#             FOREIGN KEY (repo_id) REFERENCES Repositories(repo_id)
#         );
#     """)
    
#     # Insert scores
#     for _, row in health_df.iterrows():
#         cursor.execute("""
#             INSERT INTO HealthScores 
#             (repo_id, activity_score, contributor_score, responsiveness_score, 
#              stability_score, overall_health_score, health_status)
#             VALUES (?, ?, ?, ?, ?, ?, ?)
#         """, (
#             int(row['repo_id']),
#             int(row['activity_score']),
#             int(row['contributor_score']),
#             int(row['responsiveness_score']),
#             int(row['stability_score']),
#             int(row['overall_health_score']),
#             row['health_status']
#         ))
    
#     conn.commit()
#     conn.close()
#     print(" Health scores saved to database")

# METRIC CALCULATION  

def calculate_activity_score(repo_data):
    """
    Score based on commit recency and frequency.
    30 points max. Higher = more recent commits.
    """
    days_since_commit = repo_data['days_since_last_commit']
    commits_6m = repo_data['commits_6months']
    
    # Recency score (0-20)
    if pd.isna(days_since_commit):
        recency = 0
    elif days_since_commit < 7:
        recency = 20
    elif days_since_commit < 30:
        recency = 15
    elif days_since_commit < 90:
        recency = 10
    elif days_since_commit < 180:
        recency = 5
    else:
        recency = 0
    
    # Frequency score (0-10)
    if pd.isna(commits_6m):
        frequency = 0
    elif commits_6m >= 50:
        frequency = 10
    elif commits_6m >= 20:
        frequency = 7
    elif commits_6m >= 5:
        frequency = 4
    else:
        frequency = 0
    
    return recency + frequency

def calculate_contributor_score(repo_data):
    """
    Score based on team size and diversity.
    30 points max. More contributors = lower abandonment risk.
    """
    contributors = repo_data['total_contributors']
    
    if pd.isna(contributors) or contributors == 0:
        return 0
    elif contributors >= 20:
        return 30
    elif contributors >= 10:
        return 25
    elif contributors >= 5:
        return 18
    elif contributors >= 2:
        return 10
    else:
        return 5

def calculate_responsiveness_score(repo_data):
    """
    Score based on how fast issues are resolved.
    25 points max. Faster resolution = better maintenance.
    """
    avg_close_time = repo_data['avg_days_to_close']
    open_issues = repo_data['open_issues']
    
    if pd.isna(avg_close_time):
        time_score = 0
    elif avg_close_time < 14:
        time_score = 20
    elif avg_close_time < 30:
        time_score = 15
    elif avg_close_time < 60:
        time_score = 10
    elif avg_close_time < 180:
        time_score = 5
    else:
        time_score = 0
    
    # Penalty if too many open issues (unresolved problems)
    open_penalty = 0
    if not pd.isna(open_issues):
        if open_issues > 100:
            open_penalty = 5
        elif open_issues > 50:
            open_penalty = 2
    
    return max(0, time_score - open_penalty)

def calculate_stability_score(repo_data):
    """
    Score based on consistency of updates.
    15 points max. Regular updates = stable project.
    """
    commits_6m = repo_data['commits_6months']
    authors = repo_data['unique_authors']
    
    # Regular updates score
    if pd.isna(commits_6m):
        consistency = 0
    else:
        monthly_avg = commits_6m / 6
        if monthly_avg > 10:
            consistency = 10
        elif monthly_avg > 5:
            consistency = 7
        elif monthly_avg > 1:
            consistency = 4
        else:
            consistency = 0
    
    # Diversity score (not dependent on 1-2 people)
    diversity = 0
    if not pd.isna(authors):
        if authors >= 5:
            diversity = 5
        elif authors >= 2:
            diversity = 3
    
    return consistency + diversity

#  DATA LOADING 

def load_repo_metrics():
    """Pull all metrics from database."""
    
    # Activity metrics
    activity_query = """
    SELECT 
        r.repo_id,
        r.repo_name,
        r.stars,
        DATEDIFF(DAY, MAX(c.commit_date), GETDATE()) AS days_since_last_commit,
        COUNT(DISTINCT c.commit_id) AS commits_6months
    FROM Repositories r
    LEFT JOIN Commits c ON r.repo_id = c.repo_id 
        AND c.commit_date >= DATEADD(MONTH, -6, GETDATE())
    GROUP BY r.repo_id, r.repo_name, r.stars
    """
    
    activity_df = query_database(activity_query)
    
    # Contributor metrics
    contributor_query = """
    SELECT 
        r.repo_id,
        COUNT(DISTINCT c.contributor_name) AS total_contributors,
        COUNT(DISTINCT c2.author_name) AS unique_authors
    FROM Repositories r
    LEFT JOIN Contributors c ON r.repo_id = c.repo_id
    LEFT JOIN Commits c2 ON r.repo_id = c2.repo_id
        AND c2.commit_date >= DATEADD(MONTH, -6, GETDATE())
    GROUP BY r.repo_id
    """
    
    contributor_df = query_database(contributor_query)
    
    # Issue metrics
    issue_query = """
    SELECT 
        r.repo_id,
        AVG(DATEDIFF(DAY, i.created_at, i.closed_at)) AS avg_days_to_close,
        COUNT(CASE WHEN i.issue_state = 'open' THEN 1 END) AS open_issues,
        COUNT(*) AS total_issues
    FROM Repositories r
    LEFT JOIN Issues i ON r.repo_id = i.repo_id
    GROUP BY r.repo_id
    """
    
    issue_df = query_database(issue_query)
    
    # Merge all metrics
    merged = activity_df.merge(contributor_df, on='repo_id', how='left')
    merged = merged.merge(issue_df, on='repo_id', how='left')
    
    return merged

#  HEALTH SCORE CALCULATION 

def calculate_health_scores(metrics_df):
    """Apply all scoring functions and create overall health score."""
    
    health_scores = []
    
    for _, row in metrics_df.iterrows():
        activity = calculate_activity_score(row)
        contributor = calculate_contributor_score(row)
        responsiveness = calculate_responsiveness_score(row)
        stability = calculate_stability_score(row)
        
        total_score = activity + contributor + responsiveness + stability
        
        # Status classification
        if total_score >= 80:
            status = "HEALTHY"
        elif total_score >= 50:
            status = "MODERATE"
        else:
            status = "AT RISK"
        
        health_scores.append({
            'repo_id': row['repo_id'],
            'repo_name': row['repo_name'],
            'stars': row['stars'],
            'activity_score': activity,
            'contributor_score': contributor,
            'responsiveness_score': responsiveness,
            'stability_score': stability,
            'overall_health_score': total_score,
            'health_status': status,
            'days_since_commit': row['days_since_last_commit'],
            'commits_6m': row['commits_6months'],
            'contributors': row['total_contributors'],
            'avg_issue_close_days': row['avg_days_to_close'],
            'open_issues': row['open_issues']
        })
    
    return pd.DataFrame(health_scores)

#  ANALYSIS FUNCTIONS 


def analyze_correlations(health_df):
    """
    Find relationships between metrics.
    Why this matters: Tells you which factors actually drive health.
    """
    print("\n" + "="*70)
    print("CORRELATION ANALYSIS: What Drives Repository Health?")
    print("="*70)
    
    # Does more stars = better maintenance?
    correlation_stars_health = health_df['stars'].corr(health_df['overall_health_score'])
    print(f"\n Correlation: Stars vs Health Score = {correlation_stars_health:.2f}")
    
    if pd.notna(correlation_stars_health):
        if correlation_stars_health > 0.5:
            insight = " Popular projects ARE generally better maintained"
        elif correlation_stars_health < -0.5:
            insight = "  SURPRISING: Popular projects are LESS maintained (famous abandoned projects!)"
        else:
            insight = " No clear relationship (popularity ≠ good maintenance)"
        print(f"   {insight}")
    else:
        print("    Not enough data to calculate correlation")
    
    # Does more contributors = faster issue resolution?
    if 'contributors' in health_df.columns and 'avg_issue_close_days' in health_df.columns:
        # FIX: Use dropna to remove NaN values before correlation
        valid_data = health_df[['contributors', 'avg_issue_close_days']].dropna()
        
        if len(valid_data) > 1:
            correlation_team_speed = valid_data['contributors'].corr(valid_data['avg_issue_close_days'])
            print(f"\n Correlation: Contributors vs Issue Close Time = {correlation_team_speed:.2f}")
            
            if pd.notna(correlation_team_speed):
                if correlation_team_speed < -0.5:
                    print(f"    Larger teams resolve issues FASTER (statistically significant)")
                elif correlation_team_speed < -0.3:
                    print(f"    Larger teams resolve issues somewhat faster")
                else:
                    print(f"    Team size doesn't strongly affect response speed")
        else:
            print(f"\n👥 Correlation: Contributors vs Issue Close Time = (insufficient data)")
    
    # Activity vs stability (recent updates = consistent updates?)
    correlation_activity_stability = health_df['activity_score'].corr(health_df['stability_score'])
    print(f"\n Correlation: Activity vs Stability = {correlation_activity_stability:.2f}")
    
    if pd.notna(correlation_activity_stability):
        if correlation_activity_stability > 0.6:
            print(f"    Recent projects are CONSISTENTLY active (good sign)")
        else:
            print(f"     Some projects have sporadic activity patterns")
    else:
        print(f"    Not enough data to calculate correlation")

def identify_risks(health_df):
    """Flag high-risk projects."""
    print("\n" + "="*60)
    print("RISK ANALYSIS")
    print("="*60)
    
    at_risk = health_df[health_df['health_status'] == " AT RISK"]
    print(f"\n  At-Risk Projects: {len(at_risk)}/{len(health_df)}")
    for _, repo in at_risk.iterrows():
        print(f"   • {repo['repo_name']} (Health Score: {repo['overall_health_score']})")
        if pd.notna(repo['days_since_commit']) and repo['days_since_commit'] > 180:
            print(f" -> No commits in {int(repo['days_since_commit'])} days")
        if repo['contributors'] <= 1:
            print(f"-> Only {int(repo['contributors'])} contributor(s)")
    
    # Projects with high issue backlog
    high_backlog = health_df[health_df['open_issues'] > 50].sort_values('open_issues', ascending=False)
    if len(high_backlog) > 0:
        print(f"\n High Issue Backlog:")
        for _, repo in high_backlog.head(3).iterrows():
            print(f"   • {repo['repo_name']}: {int(repo['open_issues'])} open issues")

def identify_opportunities(health_df):
    """Find high-potential projects to contribute to."""
    print("\n" + "="*60)
    print("OPPORTUNITY ANALYSIS")
    print("="*60)
    
    # Healthy and responsive
    healthy = health_df[health_df['health_status'] == " HEALTHY"].sort_values('stars', ascending=False)
    print(f"\n Best for Contributing (Healthy + Responsive):")
    for _, repo in healthy.head(5).iterrows():
        print(f"    {repo['repo_name']} ({int(repo['stars'])} stars)")
        print(f"     Health Score: {int(repo['overall_health_score'])}/100")
        if pd.notna(repo['avg_issue_close_days']):
            print(f"      Issues resolved in {int(repo['avg_issue_close_days'])} days avg")
    
    # Emerging but needs help
    moderate = health_df[health_df['health_status'] == " MODERATE"].sort_values('stars', ascending=True)
    print(f"\n Growth Projects (Moderate Health, Lower Stars):")
    for _, repo in moderate[moderate['stars'] < 5000].head(3).iterrows():
        print(f"    {repo['repo_name']} ({int(repo['stars'])} stars)")
        print(f"      Has potential but needs more contributors")

def summary_statistics(health_df):
    print("\n" + "="*60)
    print("OVERALL SUMMARY")
    print("="*60)
    
    healthy_count = len(health_df[health_df['health_status'] == "HEALTHY"])
    moderate_count = len(health_df[health_df['health_status'] == "MODERATE"])
    at_risk_count = len(health_df[health_df['health_status'] == "AT RISK"])
    
    print(f"\nHealth Distribution:")
    print(f"   Healthy: {healthy_count} projects ({healthy_count/len(health_df)*100:.0f}%)")
    print(f"   Moderate: {moderate_count} projects ({moderate_count/len(health_df)*100:.0f}%)")
    print(f"   At Risk: {at_risk_count} projects ({at_risk_count/len(health_df)*100:.0f}%)")
    
    print(f"\nAverage Scores:")
    print(f"  Activity: {health_df['activity_score'].mean():.1f}/30")
    print(f"  Contributors: {health_df['contributor_score'].mean():.1f}/30")
    print(f"  Responsiveness: {health_df['responsiveness_score'].mean():.1f}/25")
    print(f"  Stability: {health_df['stability_score'].mean():.1f}/15")
    print(f"  Overall: {health_df['overall_health_score'].mean():.1f}/100")

#  EXPORT FOR POWER BI 

def export_for_powerbi(health_df):
    """Save data to CSV for Power BI import."""
    output_file = "github_health_metrics.csv"
    health_df.to_csv(output_file, index=False)
    print(f"\n Data exported to {output_file} for Power BI Dashboard and Reporting ")
    return output_file

#  MAIN EXECUTION 

def main():
    print(" Loading GitHub health metrics from database...")
    metrics = load_repo_metrics()
    
    print(f" Analyzing {len(metrics)} repositories...\n")
    
    # Calculate health scores
    health_df = calculate_health_scores(metrics)
    
    # Display results
    print("\n" + "="*60)
    print("REPOSITORY HEALTH SCORES")
    print("="*60)
    print(health_df[['repo_name', 'stars', 'overall_health_score', 'health_status']].sort_values('overall_health_score', ascending=False).to_string(index=False))
    
    # Save to database
    # insert_health_scores(health_df)
    
    # Run analyses
    analyze_correlations(health_df)
    identify_risks(health_df)
    identify_opportunities(health_df)
    summary_statistics(health_df)
    
    # Export for Power BI
    export_for_powerbi(health_df)
    
    print("\n Analysis completed ")

if __name__ == "__main__":
    main()

