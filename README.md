# Dependency Risk Analyzer

## What This Does

This project tells you if an open-source project is safe to depend on.

Instead of guessing based on stars or last update date, this analyzes 4 real signals:
- **Activity**: Are they pushing code regularly?
- **Team Size**: Do they have enough people or is it one person?
- **Response Speed**: How fast do they fix bugs?
- **Consistency**: Are updates regular?

## The Problem It Solves

You depend on open-source projects. But:
- A project with 100K stars might be abandoned
- A small project with 5k stars might be actively maintained
- You can't tell the difference easily

This tool tells you.

## How It Works

1. **Pulls real data** from GitHub API (commits, issues, contributors)
2. **Scores each project** on 4 dimensions (0-100 scale)
3. **Shows which are risky** (visualization in Power BI)
4. **Identifies patterns** (eg: popular != maintained)

## Key Finding

- Found a -0.72 correlation between popularity and maintenance.
  Translation: Famous projects aren't always maintained well.
  
- Team Size Strongly Predicts Maintenance Speed:
  Projects with larger teams close issues 3x faster than solo maintainers.
  
- Issue Backlogs Indicate Problems:
  High-backlog projects (>100 open issues):
    PyTorch: 165 open issues
    TensorFlow: 161 open issues
    Kubernetes: 144 open issues
  These projects have maintenance problems despite being "healthy" overall.
  
- Portfolio Health Breakdown:
  Activity Score:    27.0/30  (Very active)
  Team Size:         24.0/30  (Large teams)
  Response Speed:    12.8/25  (Moderate - some backlog)
  Consistency:       13.5/15  (Regular updates)
  __________________________
  Overall Average:   77.3/100 (Good portfolio health)
  

## Tech Stack

- **SQL**: Store and organize data
- **Python**: Calculate health scores
- **Power BI**: Visualize insights

## Project Structure

dependency-risk-analyzer/
 sql:
 DDL Script.sql (Database setup) 
 DataAnalysis.sql (Explored data)

 python : 
 DataFetching.py (Pull data from GitHub)
 analyze_github_health.py    (Calculate scores)

 powerbi:
 Dashboard and Reporting.pbix  (interactive visualization)

 README.md
 
##Key Insights : Addessed 

- Data Quality Matters - React scored 0 because GitHub API rate-limits large repos. Data completeness beats   data volume.

- Correlation ≠ Causation - Stars and health correlate at -0.72, but that's partly due to API limitations,     not real abandonment.

- Design Scoring Systems - Weighting decisions matter. Why 30% for activity but 15% for stability? Because    different metrics have different business impact.

- API Constraints Are Real - GitHub limits 5,000 API calls/hour. Large projects need special handling.

## Results

Analyzed 10 major projects:
- 8 marked as healthy
- 2 marked as at-risk
- Identified projects with 100K+ stars but low maintenance

## Limitations

- GitHub API rate-limits large projects. 
  React and Linux repos only have 300 commits instead of all commits. 
  This affects their scores but teaches an important lesson: data completeness matters.
  
- 6-Month Window
  Analysis only looks at last 6 months.
  Doesn't capture long-term trends.
  Fix: Store historical data and track changes over time.
  
- Issue Data Quality
  Some repos have mostly OPEN issues (no closed_at date).
  Responsiveness score is harder to calculate.
  Fix: Fetch more closed issues or adjust weighting.
