"""
Security Check Before GitHub Push
Run this script to verify no credentials will be exposed
"""
import os
import re

def check_file_for_credentials(filepath):
    """Check if file contains potential credentials"""
    sensitive_patterns = [
        r'AKIA[0-9A-Z]{16}',  # AWS Access Key
        r'aws_secret_access_key\s*=\s*["\']?[A-Za-z0-9/+=]{40}',  # AWS Secret
        r'password\s*=\s*["\'][^"\']+["\']',  # Passwords
        r'secret_key\s*=\s*["\'][^"\']+["\']',  # Secret keys
    ]
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        for pattern in sensitive_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True
    except:
        pass
    
    return False

def main():
    print("="*70)
    print("  SECURITY CHECK BEFORE GITHUB PUSH")
    print("="*70)
    print()
    
    # Check if .gitignore exists
    if not os.path.exists('.gitignore'):
        print("❌ ERROR: .gitignore file not found!")
        print("   Create .gitignore before pushing to GitHub")
        return False
    else:
        print("✅ .gitignore file exists")
    
    # Check if .env is in .gitignore
    with open('.gitignore', 'r') as f:
        gitignore_content = f.read()
        if '.env' in gitignore_content:
            print("✅ .env is in .gitignore")
        else:
            print("❌ ERROR: .env is NOT in .gitignore!")
            return False
    
    # Check if .env exists (should not be pushed)
    if os.path.exists('.env'):
        print("✅ .env file exists locally (will be ignored by git)")
    
    # Check .env.example for credentials
    if os.path.exists('.env.example'):
        if check_file_for_credentials('.env.example'):
            print("❌ WARNING: .env.example may contain real credentials!")
            print("   Please replace with placeholders")
            return False
        else:
            print("✅ .env.example is clean (no credentials)")
    
    # Check main files
    files_to_check = ['app.py', 'README.md']
    all_clean = True
    
    for filepath in files_to_check:
        if os.path.exists(filepath):
            if check_file_for_credentials(filepath):
                print(f"❌ WARNING: {filepath} may contain credentials!")
                all_clean = False
            else:
                print(f"✅ {filepath} is clean")
    
    print()
    print("="*70)
    
    if all_clean:
        print("✅ SECURITY CHECK PASSED!")
        print()
        print("Safe to push to GitHub. Run:")
        print("  git add .")
        print("  git commit -m 'Initial commit'")
        print("  git push -u origin main")
        print()
        return True
    else:
        print("❌ SECURITY CHECK FAILED!")
        print()
        print("Fix the issues above before pushing to GitHub")
        print()
        return False

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
