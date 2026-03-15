#!/usr/bin/env python3
"""
Tests for gitpull

Run with: python3 test_gitpull.py
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Import the module to test
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gitpull


class TestGitPull(unittest.TestCase):
    """Test cases for the gitpull module."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.test_repo_url = "https://github.com/gutenbergbooks/99999.git"
    
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_is_git_repo_positive(self):
        """Test is_git_repo returns True for a git repository."""
        repo_path = os.path.join(self.test_dir, "test_repo")
        subprocess.run(["git", "init", repo_path], check=True, capture_output=True)
        self.assertTrue(gitpull.is_git_repo(repo_path))
    
    def test_is_git_repo_negative(self):
        """Test is_git_repo returns False for a non-git directory."""
        non_repo_path = os.path.join(self.test_dir, "not_a_repo")
        os.makedirs(non_repo_path)
        self.assertFalse(gitpull.is_git_repo(non_repo_path))
    
    def test_clone_repo(self):
        """Test cloning a repository."""
        target_path = os.path.join(self.test_dir, "cloned_repo")
        gitpull.clone_repo(self.test_repo_url, target_path)
        self.assertTrue(os.path.exists(target_path))
        self.assertTrue(gitpull.is_git_repo(target_path))
    
    def test_pull_repo(self):
        """Test pulling changes in an existing repository."""
        repo_path = os.path.join(self.test_dir, "existing_repo")
        gitpull.clone_repo(self.test_repo_url, repo_path)
        # Pull should succeed without errors
        gitpull.pull_repo(repo_path)
        self.assertTrue(gitpull.is_git_repo(repo_path))
    
    def test_update_folder_new_target(self):
        """Test update_folder with a new target path."""
        target_path = os.path.join(self.test_dir, "new_target")
        result = gitpull.update_folder(self.test_repo_url, target_path)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(target_path))
        self.assertTrue(gitpull.is_git_repo(target_path))
    
    def test_update_folder_existing_repo_same_remote(self):
        """Test update_folder with an existing repo with the same remote."""
        target_path = os.path.join(self.test_dir, "existing_target")
        # First clone
        gitpull.update_folder(self.test_repo_url, target_path)
        # Second update should pull
        result = gitpull.update_folder(self.test_repo_url, target_path)
        self.assertTrue(result)
        self.assertTrue(gitpull.is_git_repo(target_path))
    
    def test_update_folder_existing_repo_different_remote(self):
        """Test update_folder with an existing repo with a different remote."""
        target_path = os.path.join(self.test_dir, "different_remote")
        # Clone with one URL
        gitpull.update_folder(self.test_repo_url, target_path)
        # Try to update with a different URL
        different_url = "https://github.com/torvalds/linux.git"
        result = gitpull.update_folder(different_url, target_path)
        self.assertFalse(result)
    
    def test_update_folder_existing_non_empty_non_git(self):
        """Test update_folder with an existing non-empty non-git directory."""
        target_path = os.path.join(self.test_dir, "non_git")
        os.makedirs(target_path)
        # Create a file in the directory
        with open(os.path.join(target_path, "test.txt"), "w") as f:
            f.write("test")
        result = gitpull.update_folder(self.test_repo_url, target_path)
        self.assertFalse(result)
    
    def test_get_remote_url(self):
        """Test getting the remote URL of a repository."""
        repo_path = os.path.join(self.test_dir, "test_remote")
        gitpull.clone_repo(self.test_repo_url, repo_path)
        remote_url = gitpull.get_remote_url(repo_path)
        self.assertEqual(remote_url, self.test_repo_url)

    def test_norepo_option(self):
        """Test the --norepo option with a non-repository directory."""
        target_path = os.path.join(self.test_dir, "norepo_test")
        os.makedirs(target_path)

        result = subprocess.run(
            ["python3", "gitpull.py", "--norepo", "77044", target_path],
            capture_output=True,
            text=True
        )
        self.assertEqual(result.returncode, 0)
        bookdir= os.path.join(target_path, "77044")
        self.assertTrue(os.path.exists(bookdir))
        self.assertFalse(gitpull.is_git_repo(bookdir))
def main():
    """Run the tests."""
    unittest.main(verbosity=2)


if __name__ == "__main__":
    main()
