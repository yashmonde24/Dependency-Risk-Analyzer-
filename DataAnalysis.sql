
--Query 1: Which repos are inactive?
--Insights : How long since each repo got a code update. High number = abandoned.
-- Find repos with no commits in last 6 months (potential abandonment)
SELECT 
    repo_name,
    full_name,
    stars,
    DATEDIFF(DAY, MAX(c.commit_date), GETDATE()) AS days_since_last_commit,
    COUNT(DISTINCT c.commit_id) AS total_commits_6months
FROM Repositories r
LEFT JOIN Commits c ON r.repo_id = c.repo_id 
    AND c.commit_date >= DATEADD(MONTH, -6, GETDATE())
GROUP BY r.repo_id, r.repo_name, r.full_name, r.stars
ORDER BY days_since_last_commit DESC;

 -- Query 2:Which repos have the most active maintenance?
 --Insights: Which repos have the most active development. Higher commit count = more actively maintained.
 -- Calculate commit velocity (commits per month in last 6 months)
SELECT 
    r.repo_name,
    r.stars,
    COUNT(DISTINCT c.commit_id) AS commits_6months,
    COUNT(DISTINCT c.author_name) AS unique_authors,
    ROUND(CAST(COUNT(DISTINCT c.commit_id) as float) / 6, 2) AS avg_commits_per_month
FROM Repositories r
LEFT JOIN Commits c ON r.repo_id = c.repo_id 
    AND c.commit_date >= DATEADD(MONTH, -6, GETDATE())
GROUP BY r.repo_id, r.repo_name, r.stars
ORDER BY commits_6months DESC;

--Query 3: How fast do repos resolve issues?
-- Insight : What this shows: Are they responsive to user problems? Low number = good maintenance.
-- Calculate average issue resolution time (for closed issues)
SELECT 
    r.repo_name,
    r.stars,
    COUNT(*) AS total_issues_closed,
    AVG(DATEDIFF(DAY, i.created_at, i.closed_at)) AS avg_days_to_close,
    COUNT(CASE WHEN issue_state = 'open' THEN 1 END) AS open_issues
FROM Repositories r
LEFT JOIN Issues i ON r.repo_id = i.repo_id
WHERE i.closed_at IS NOT NULL
GROUP BY r.repo_id, r.repo_name, r.stars
ORDER BY avg_days_to_close ASC;

-- Query 4: Team size and contributor diversity
-- Insight : Is development spread across a team or dependent on 1-2 people?
-- How many people contribute to each repo?
SELECT 
    r.repo_name,
    r.stars,
    COUNT(*) AS total_contributors,
    SUM(ISNULL(c.contribution_count,0)) AS total_contributions,
    ROUND(AVG(CAST(ISNULL(c.contribution_count ,0 )AS FLOAT)), 2) AS avg_contributions_per_person,
    MAX(ISNULL(c.contribution_count,0)) AS top_contributor_count
FROM Repositories r
LEFT JOIN Contributors c ON r.repo_id = c.repo_id
GROUP BY r.repo_id, r.repo_name, r.stars
ORDER BY total_contributors DESC

-- Query 5: Repositories Health Score 
--Insight : A single score (0-100) that combines activity, team size, and responsiveness.
-- Create a health score combining multiple signals
WITH repo_metrics AS (
    SELECT 
        r.repo_id,
        r.repo_name,
        r.stars,
        -- Activity score (0-30 points)
        CASE 
            WHEN DATEDIFF(DAY, MAX(c.commit_date), GETDATE()) < 30 THEN 30
            WHEN DATEDIFF(DAY, MAX(c.commit_date), GETDATE()) < 90 THEN 20
            WHEN DATEDIFF(DAY, MAX(c.commit_date), GETDATE()) < 180 THEN 10
            ELSE 0
        END AS activity_score,
        
        -- Contributor score (0-30 points)
        CASE 
            WHEN COUNT(DISTINCT c2.contributor_name) >= 10 THEN 30
            WHEN COUNT(DISTINCT c2.contributor_name) >= 5 THEN 20
            WHEN COUNT(DISTINCT c2.contributor_name) >= 1 THEN 10
            ELSE 0
        END AS contributor_score,
        
        -- Issue responsiveness (0-40 points)
        CASE 
            WHEN AVG(DATEDIFF(DAY, i.created_at, i.closed_at)) < 30 THEN 40
            WHEN AVG(DATEDIFF(DAY, i.created_at, i.closed_at)) < 60 THEN 25
            WHEN AVG(DATEDIFF(DAY, i.created_at, i.closed_at)) < 120 THEN 15
            ELSE 5
        END AS responsiveness_score
    FROM Repositories r
    LEFT JOIN Commits c ON r.repo_id = c.repo_id
    LEFT JOIN Contributors c2 ON r.repo_id = c2.repo_id
    LEFT JOIN Issues i ON r.repo_id = i.repo_id AND i.closed_at IS NOT NULL
    GROUP BY r.repo_id, r.repo_name, r.stars
)
SELECT 
    repo_name,
    stars,
    activity_score,
    contributor_score,
    responsiveness_score,
    (activity_score + contributor_score + responsiveness_score) AS health_score,
    CASE 
        WHEN (activity_score + contributor_score + responsiveness_score) >= 80 THEN 'HEALTHY'
        WHEN (activity_score + contributor_score + responsiveness_score) >= 50 THEN 'MODERATE'
        ELSE 'AT RISK'
    END AS health_status
FROM repo_metrics
ORDER BY health_score DESC;