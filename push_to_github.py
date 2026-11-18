"""
GitHub Push Utility for AASHA_MINI_PROJECT
Pushes the local repository to https://github.com/Prince2500/AASHA_MINI_PROJECT.git
"""

import os
import sys
from dulwich import porcelain

def push_project():
    token = os.environ.get('GITHUB_TOKEN')
    if not token and len(sys.argv) > 1:
        token = sys.argv[1].strip()
        
    if not token:
        print("GitHub requires authentication to push to: https://github.com/Prince2500/AASHA_MINI_PROJECT.git")
        print("\nUsage Options:")
        print("1. Pass token as argument: python push_to_github.py YOUR_GITHUB_PERSONAL_ACCESS_TOKEN")
        print("2. Or set environment variable: $env:GITHUB_TOKEN='YOUR_TOKEN'; python push_to_github.py")
        print("3. Or enter token below:")
        try:
            token = input("Enter GitHub Personal Access Token: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nPush cancelled.")
            return

    if not token:
        print("No token provided. Push aborted.")
        return

    print("Pushing to https://github.com/Prince2500/AASHA_MINI_PROJECT.git on branch 'main'...")
    remote_url = f"https://{token}@github.com/Prince2500/AASHA_MINI_PROJECT.git"
    try:
        porcelain.push('.', remote_url, 'refs/heads/main')
        print("\n SUCCESS! All code has been pushed to https://github.com/Prince2500/AASHA_MINI_PROJECT.git")
    except Exception as e:
        print(f"\n Error pushing to GitHub: {e}")
        print("Please verify that your Personal Access Token has 'repo' / 'contents:write' permissions.")

if __name__ == '__main__':
    push_project()
