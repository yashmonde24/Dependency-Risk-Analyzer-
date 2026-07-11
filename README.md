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
- A small project with 5 stars might be actively maintained
- You can't tell the difference easily

This tool tells you.

## How It Works

1. **Pulls real data** from GitHub API (commits, issues, contributors)
2. **Scores each project** on 4 dimensions (0-100 scale)
3. **Shows which are risky** (visualization in Power BI)
4. **Identifies patterns** (e.g., popular != maintained)

## Key Finding

Found a -0.72 correlation between popularity and maintenance.
Translation: Famous projects aren't always maintained well.

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

## Results

Analyzed 10 major projects:
- 8 marked as healthy
- 2 marked as at-risk
- Identified projects with 100K+ stars but low maintenance

## Limitations

GitHub API rate-limits large projects. 
React and Linux repos only have 300 commits instead of all commits. 
This affects their scores but teaches an important lesson: data completeness matters.
