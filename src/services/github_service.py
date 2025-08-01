"""
GitHub Service Module
Handles all GitHub API operations for Jarvis autonomy
"""

import os
import base64
import json
from datetime import datetime
from github import Github, GithubException
from flask import current_app
from typing import Dict, List, Optional, Tuple

class GitHubService:
    def __init__(self):
        self.token = os.getenv('GITHUB_TOKEN')
        self.username = os.getenv('GITHUB_USERNAME')
        self.default_repo = os.getenv('GITHUB_REPO', 'jarvis-deploy')
        self.default_branch = os.getenv('GITHUB_BRANCH', 'main')
        
        if not self.token:
            raise ValueError("GITHUB_TOKEN environment variable is required")
        
        self.github = Github(self.token)
        self.user = self.github.get_user()
    
    def create_repository(self, repo_name: str, description: str = "Jarvis autonomous deployment repository", private: bool = False) -> Dict:
        """Create a new GitHub repository"""
        try:
            repo = self.user.create_repo(
                name=repo_name,
                description=description,
                private=private,
                auto_init=True
            )
            
            return {
                "status": "success",
                "message": f"Repository '{repo_name}' created successfully",
                "repo_url": repo.html_url,
                "clone_url": repo.clone_url,
                "ssh_url": repo.ssh_url
            }
        except GithubException as e:
            return {
                "status": "error",
                "message": f"Failed to create repository: {e.data.get('message', str(e))}"
            }
    
    def get_repository(self, repo_name: str = None) -> object:
        """Get repository object"""
        repo_name = repo_name or self.default_repo
        try:
            return self.user.get_repo(repo_name)
        except GithubException as e:
            raise Exception(f"Repository '{repo_name}' not found: {e.data.get('message', str(e))}")
    
    def list_repositories(self) -> List[Dict]:
        """List all repositories for the authenticated user"""
        try:
            repos = []
            for repo in self.user.get_repos():
                repos.append({
                    "name": repo.name,
                    "full_name": repo.full_name,
                    "description": repo.description,
                    "private": repo.private,
                    "html_url": repo.html_url,
                    "clone_url": repo.clone_url,
                    "default_branch": repo.default_branch,
                    "created_at": repo.created_at.isoformat(),
                    "updated_at": repo.updated_at.isoformat()
                })
            return repos
        except GithubException as e:
            raise Exception(f"Failed to list repositories: {e.data.get('message', str(e))}")
    
    def create_or_update_file(self, file_path: str, content: str, commit_message: str, 
                             repo_name: str = None, branch: str = None) -> Dict:
        """Create or update a file in the repository"""
        repo_name = repo_name or self.default_repo
        branch = branch or self.default_branch
        
        try:
            repo = self.get_repository(repo_name)
            
            # Check if file exists
            try:
                file_obj = repo.get_contents(file_path, ref=branch)
                # File exists, update it
                result = repo.update_file(
                    path=file_path,
                    message=commit_message,
                    content=content,
                    sha=file_obj.sha,
                    branch=branch
                )
                action = "updated"
            except GithubException:
                # File doesn't exist, create it
                result = repo.create_file(
                    path=file_path,
                    message=commit_message,
                    content=content,
                    branch=branch
                )
                action = "created"
            
            return {
                "status": "success",
                "action": action,
                "message": f"File '{file_path}' {action} successfully",
                "commit_sha": result['commit'].sha,
                "commit_url": result['commit'].html_url,
                "file_url": result['content'].html_url
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to {action if 'action' in locals() else 'create/update'} file: {str(e)}"
            }
    
    def delete_file(self, file_path: str, commit_message: str, 
                   repo_name: str = None, branch: str = None) -> Dict:
        """Delete a file from the repository"""
        repo_name = repo_name or self.default_repo
        branch = branch or self.default_branch
        
        try:
            repo = self.get_repository(repo_name)
            file_obj = repo.get_contents(file_path, ref=branch)
            
            result = repo.delete_file(
                path=file_path,
                message=commit_message,
                sha=file_obj.sha,
                branch=branch
            )
            
            return {
                "status": "success",
                "message": f"File '{file_path}' deleted successfully",
                "commit_sha": result['commit'].sha,
                "commit_url": result['commit'].html_url
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to delete file: {str(e)}"
            }
    
    def get_file_content(self, file_path: str, repo_name: str = None, branch: str = None) -> Dict:
        """Get content of a file from the repository"""
        repo_name = repo_name or self.default_repo
        branch = branch or self.default_branch
        
        try:
            repo = self.get_repository(repo_name)
            file_obj = repo.get_contents(file_path, ref=branch)
            
            # Decode content if it's base64 encoded
            content = file_obj.content
            if file_obj.encoding == 'base64':
                content = base64.b64decode(content).decode('utf-8')
            
            return {
                "status": "success",
                "content": content,
                "sha": file_obj.sha,
                "size": file_obj.size,
                "encoding": file_obj.encoding,
                "download_url": file_obj.download_url,
                "html_url": file_obj.html_url
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to get file content: {str(e)}"
            }
    
    def list_files(self, directory_path: str = "", repo_name: str = None, branch: str = None) -> List[Dict]:
        """List files in a directory"""
        repo_name = repo_name or self.default_repo
        branch = branch or self.default_branch
        
        try:
            repo = self.get_repository(repo_name)
            contents = repo.get_contents(directory_path, ref=branch)
            
            files = []
            for content in contents:
                files.append({
                    "name": content.name,
                    "path": content.path,
                    "type": content.type,  # 'file' or 'dir'
                    "size": content.size,
                    "sha": content.sha,
                    "download_url": content.download_url,
                    "html_url": content.html_url
                })
            
            return files
            
        except Exception as e:
            raise Exception(f"Failed to list files: {str(e)}")
    
    def create_branch(self, branch_name: str, source_branch: str = None, 
                     repo_name: str = None) -> Dict:
        """Create a new branch"""
        repo_name = repo_name or self.default_repo
        source_branch = source_branch or self.default_branch
        
        try:
            repo = self.get_repository(repo_name)
            source_ref = repo.get_git_ref(f"heads/{source_branch}")
            
            repo.create_git_ref(
                ref=f"refs/heads/{branch_name}",
                sha=source_ref.object.sha
            )
            
            return {
                "status": "success",
                "message": f"Branch '{branch_name}' created successfully",
                "branch_name": branch_name,
                "source_branch": source_branch
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to create branch: {str(e)}"
            }
    
    def get_commit_history(self, repo_name: str = None, branch: str = None, limit: int = 10) -> List[Dict]:
        """Get commit history"""
        repo_name = repo_name or self.default_repo
        branch = branch or self.default_branch
        
        try:
            repo = self.get_repository(repo_name)
            commits = repo.get_commits(sha=branch)[:limit]
            
            history = []
            for commit in commits:
                history.append({
                    "sha": commit.sha,
                    "message": commit.commit.message,
                    "author": commit.commit.author.name,
                    "author_email": commit.commit.author.email,
                    "date": commit.commit.author.date.isoformat(),
                    "html_url": commit.html_url
                })
            
            return history
            
        except Exception as e:
            raise Exception(f"Failed to get commit history: {str(e)}")
    
    def deploy_code(self, code: str, file_path: str, commit_message: str = None, 
                   repo_name: str = None, branch: str = None) -> Dict:
        """Deploy code to GitHub repository"""
        repo_name = repo_name or self.default_repo
        branch = branch or self.default_branch
        
        if not commit_message:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            commit_message = f"Jarvis: Auto-deploy code update - {timestamp}"
        
        return self.create_or_update_file(
            file_path=file_path,
            content=code,
            commit_message=commit_message,
            repo_name=repo_name,
            branch=branch
        )
    
    def get_repository_info(self, repo_name: str = None) -> Dict:
        """Get detailed repository information"""
        repo_name = repo_name or self.default_repo
        
        try:
            repo = self.get_repository(repo_name)
            
            return {
                "name": repo.name,
                "full_name": repo.full_name,
                "description": repo.description,
                "private": repo.private,
                "html_url": repo.html_url,
                "clone_url": repo.clone_url,
                "ssh_url": repo.ssh_url,
                "default_branch": repo.default_branch,
                "language": repo.language,
                "size": repo.size,
                "stargazers_count": repo.stargazers_count,
                "watchers_count": repo.watchers_count,
                "forks_count": repo.forks_count,
                "open_issues_count": repo.open_issues_count,
                "created_at": repo.created_at.isoformat(),
                "updated_at": repo.updated_at.isoformat(),
                "pushed_at": repo.pushed_at.isoformat() if repo.pushed_at else None
            }
            
        except Exception as e:
            raise Exception(f"Failed to get repository info: {str(e)}")

# Global instance
github_service = GitHubService()

