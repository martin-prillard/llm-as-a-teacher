"""
Git handler for accessing GitHub repositories.
Uses GitHub API and MCP server when available.
"""

import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Optional, List, Tuple
import json


class GitHandler:
    """Handle GitHub repository access and code extraction."""
    
    def __init__(self):
        self.github_token = os.getenv('GITHUB_TOKEN')
        self.temp_dir = None
    
    def get_repository_info(self, git_url: str) -> Optional[Dict]:
        """
        Get repository information and code structure.
        
        Args:
            git_url: GitHub repository URL
            
        Returns:
            Dictionary with repository information and code
        """
        # Extract owner and repo from URL
        owner, repo = self._parse_github_url(git_url)
        if not owner or not repo:
            raise ValueError(f"Invalid GitHub URL: {git_url}")
        
        # Try to get info via GitHub API first
        repo_info = self._get_repo_via_api(owner, repo)
        
        # If API fails, clone the repo
        if not repo_info:
            repo_info = self._get_repo_via_clone(git_url)
        
        return repo_info
    
    def _parse_github_url(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse GitHub URL to extract owner and repo name."""
        patterns = [
            r'github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$',
            r'github\.com[:/]([^/]+)/([^/]+?)(?:/.*)?$',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1), match.group(2).rstrip('/')
        
        return None, None
    
    def _get_repo_via_api(self, owner: str, repo: str) -> Optional[Dict]:
        """Try to get repository info via GitHub API."""
        if not self.github_token:
            return None
        
        try:
            import requests
            
            headers = {
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            # Get repository info
            api_url = f'https://api.github.com/repos/{owner}/{repo}'
            response = requests.get(api_url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                return None
            
            repo_data = response.json()
            
            # Get repository contents (limited to top-level files)
            contents_url = f'https://api.github.com/repos/{owner}/{repo}/contents'
            contents_response = requests.get(contents_url, headers=headers, timeout=10)
            
            files_info = []
            if contents_response.status_code == 200:
                contents = contents_response.json()
                files_info = self._extract_files_info(contents, owner, repo, headers)
            
            return {
                'name': repo_data.get('name', repo),
                'full_name': repo_data.get('full_name', f'{owner}/{repo}'),
                'description': repo_data.get('description', ''),
                'language': repo_data.get('language', 'Unknown'),
                'url': repo_data.get('html_url', f'https://github.com/{owner}/{repo}'),
                'files': files_info,
                'source': 'api'
            }
        except Exception:
            return None
    
    def _extract_files_info(
        self, 
        contents: List, 
        owner: str, 
        repo: str, 
        headers: Dict,
        max_files: int = 50
    ) -> List[Dict]:
        """Recursively extract file information from repository."""
        import requests
        
        files_info = []
        
        for item in contents[:max_files]:
            if item['type'] == 'file':
                # Get file content for code files
                if self._is_code_file(item['name']):
                    try:
                        file_response = requests.get(
                            item['download_url'],
                            headers=headers,
                            timeout=5
                        )
                        if file_response.status_code == 200:
                            files_info.append({
                                'path': item['path'],
                                'name': item['name'],
                                'content': file_response.text[:50000],  # Limit size
                                'size': item['size']
                            })
                    except Exception:
                        pass
            elif item['type'] == 'dir' and len(files_info) < max_files:
                # Recursively get directory contents
                try:
                    dir_response = requests.get(
                        item['url'],
                        headers=headers,
                        timeout=5
                    )
                    if dir_response.status_code == 200:
                        files_info.extend(
                            self._extract_files_info(
                                dir_response.json(),
                                owner,
                                repo,
                                headers,
                                max_files - len(files_info)
                            )
                        )
                except Exception:
                    pass
        
        return files_info
    
    def _get_repo_via_clone(self, git_url: str) -> Optional[Dict]:
        """Clone repository and extract code information."""
        try:
            # Create temporary directory
            self.temp_dir = tempfile.mkdtemp(prefix='repo_eval_')
            repo_path = Path(self.temp_dir) / 'repo'
            
            # Clone repository
            subprocess.run(
                ['git', 'clone', '--depth', '1', git_url, str(repo_path)],
                check=True,
                capture_output=True,
                timeout=60
            )
            
            # Extract code files
            files_info = self._scan_repository(repo_path)
            
            return {
                'name': repo_path.name,
                'full_name': git_url.split('/')[-1].replace('.git', ''),
                'description': '',
                'language': self._detect_language(files_info),
                'url': git_url,
                'files': files_info,
                'source': 'clone',
                'local_path': str(repo_path)
            }
        except Exception as e:
            return None
    
    def _scan_repository(self, repo_path: Path, max_files: int = 50) -> List[Dict]:
        """Scan repository for code files."""
        files_info = []
        
        # Common code file extensions
        code_extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h',
            '.cs', '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala',
            '.html', '.css', '.vue', '.svelte', '.json', '.yaml', '.yml',
            '.md', '.sh', '.sql', '.r', '.m', '.ml', '.fs'
        }
        
        # Ignore common directories
        ignore_dirs = {
            '.git', '__pycache__', 'node_modules', '.venv', 'venv',
            'env', '.env', 'dist', 'build', '.idea', '.vscode', 'target'
        }
        
        for file_path in repo_path.rglob('*'):
            if file_path.is_file():
                # Skip ignored directories
                if any(ignore in file_path.parts for ignore in ignore_dirs):
                    continue
                
                # Check if it's a code file
                if file_path.suffix in code_extensions:
                    try:
                        content = file_path.read_text(encoding='utf-8', errors='ignore')
                        # Limit file size
                        if len(content) > 50000:
                            content = content[:50000] + "\n... (truncated)"
                        
                        files_info.append({
                            'path': str(file_path.relative_to(repo_path)),
                            'name': file_path.name,
                            'content': content,
                            'size': file_path.stat().st_size
                        })
                        
                        if len(files_info) >= max_files:
                            break
                    except Exception:
                        pass
        
        return files_info
    
    def _is_code_file(self, filename: str) -> bool:
        """Check if file is a code file."""
        code_extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h',
            '.cs', '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala',
            '.html', '.css', '.vue', '.svelte', '.json', '.yaml', '.yml',
            '.md', '.sh', '.sql', '.r', '.m', '.ml', '.fs'
        }
        return any(filename.endswith(ext) for ext in code_extensions)
    
    def _detect_language(self, files_info: List[Dict]) -> str:
        """Detect primary programming language from files."""
        if not files_info:
            return 'Unknown'
        
        extensions = {}
        for file_info in files_info:
            ext = Path(file_info['name']).suffix
            extensions[ext] = extensions.get(ext, 0) + 1
        
        if not extensions:
            return 'Unknown'
        
        # Map extensions to languages
        lang_map = {
            '.py': 'Python', '.js': 'JavaScript', '.ts': 'TypeScript',
            '.java': 'Java', '.cpp': 'C++', '.c': 'C', '.cs': 'C#',
            '.go': 'Go', '.rs': 'Rust', '.rb': 'Ruby', '.php': 'PHP',
            '.swift': 'Swift', '.kt': 'Kotlin', '.scala': 'Scala',
            '.html': 'HTML', '.css': 'CSS', '.vue': 'Vue', '.r': 'R'
        }
        
        most_common_ext = max(extensions.items(), key=lambda x: x[1])[0]
        return lang_map.get(most_common_ext, most_common_ext[1:].upper() if most_common_ext else 'Unknown')
    
    def cleanup(self):
        """Clean up temporary directories."""
        if self.temp_dir and Path(self.temp_dir).exists():
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)

