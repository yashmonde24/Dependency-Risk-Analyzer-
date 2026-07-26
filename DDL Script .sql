-- Create database
CREATE DATABASE GitHubHealthAnalytics;
GO

USE GitHubHealthAnalytics;
GO

-- Table 1: Core repository information
CREATE TABLE Repositories (
    repo_id BIGINT PRIMARY KEY,
    repo_name NVARCHAR(255) NOT NULL,
    owner_name NVARCHAR(255) NOT NULL,
    full_name NVARCHAR(500) NOT NULL,
    url NVARCHAR(500),
    description NVARCHAR(1000),
    stars INT,
    forks INT,
    watchers INT,
    open_issues INT,
    created_at DATETIME,
    last_updated DATETIME,
    is_archived BIT,
    language NVARCHAR(100),
    fetched_date DATETIME DEFAULT GETDATE()
);

-- Table 2: Commit activity
CREATE TABLE Commits (
    commit_id NVARCHAR(100) PRIMARY KEY,
    repo_id BIGINT,
    commit_date DATETIME,
    author_name NVARCHAR(255),
    message NVARCHAR(MAX),
    fetched_date DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (repo_id) REFERENCES Repositories(repo_id)
);

-- Table 3: Issues (questions/bugs)
CREATE TABLE Issues (
    issue_id BIGINT PRIMARY KEY,
    repo_id BIGINT,
    issue_title NVARCHAR(500),
    issue_state NVARCHAR(50), -- 'open' or 'closed'
    created_at DATETIME,
    closed_at DATETIME,
    fetched_date DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (repo_id) REFERENCES Repositories(repo_id)
);

-- Table 4: Contributors
CREATE TABLE Contributors (
    contributor_id INT PRIMARY KEY IDENTITY(1,1),
    repo_id BIGINT,
    contributor_name NVARCHAR(255),
    contribution_count INT,
    fetched_date DATETIME DEFAULT GETDATE(),
    FOREIGN KEY (repo_id) REFERENCES Repositories(repo_id)
);

-- Create indexes for faster queries
CREATE INDEX idx_repo_created ON Repositories(created_at);
CREATE INDEX idx_commit_date ON Commits(commit_date);
CREATE INDEX idx_issue_state ON Issues(issue_state, created_at);
CREATE INDEX idx_contrib_repo ON Contributors(repo_id);

GO

GO
/*
IF EXISTS (SELECT 1 FROM Contributors)
    DELETE FROM Contributors;

IF EXISTS (SELECT 1 FROM Issues)
    DELETE FROM Issues;

IF EXISTS (SELECT 1 FROM Commits)
    DELETE FROM Commits;

IF EXISTS (SELECT 1 FROM Repositories)
    DELETE FROM Repositories;

DBCC CHECKIDENT ('Contributors', RESEED, 0);
GO
*/

