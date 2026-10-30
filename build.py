#!/usr/bin/env python3
"""
Automated Build Script for IPOUtility & manage binaries
Usage:
    python build.py
    python build.py --clean
"""

import os
import sys
import shutil
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def print_header(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def run_cmd(cmd, step_name):
    print(f"\n▶ Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=BASE_DIR)
    if result.returncode != 0:
        print(f"\n❌ Error during: {step_name} (Exit code {result.returncode})")
        sys.exit(result.returncode)
    print(f"✔ Completed: {step_name}")

def get_version():
    ver_file = os.path.join(BASE_DIR, "latest_version.txt")
    if os.path.exists(ver_file):
        with open(ver_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    return "1.0.0"

def ask_user_confirmations():
    print_header("Build Pre-Flight Checklist")
    
    current_ver = get_version()
    print(f"ℹ Current version in 'latest_version.txt': {current_ver}")
    
    # Question 1: Version check
    ans1 = input("\n👉 For this build, did you update the version number in 'latest_version.txt' and 'Setup.py'? (y/n): ").strip().lower()
    if ans1 not in ["y", "yes"]:
        print("\n" + "!" * 65)
        print("❌ BUILD STOPPED:")
        print("   Please update the version number in 'latest_version.txt' and 'Setup.py'")
        print("   Refer to the documentation (EXE_Instructions.md / Developer Guide) for details.")
        print("!" * 65 + "\n")
        sys.exit(1)
        
    # Question 2: Migration / DB Version check
    ans2 = input("👉 Does this update include database migrations or model changes? (y/n): ").strip().lower()
    if ans2 in ["y", "yes"]:
        ans2_db = input("   👉 Did you increment LOCAL_DB_VERSION in 'Setup.py' (line ~71)? (y/n): ").strip().lower()
        if ans2_db not in ["y", "yes"]:
            print("\n" + "!" * 65)
            print("❌ BUILD STOPPED:")
            print("   Since this update contains model/migration changes, you must increment")
            print("   'LOCAL_DB_VERSION' in 'Setup.py' so existing clients migrate their DB.")
            print("   Refer to the documentation (EXE_Instructions.md / Developer Guide).")
            print("!" * 65 + "\n")
            sys.exit(1)
            
    print("✔ Pre-flight confirmations passed. Proceeding with build...\n")

def verify_files():
    print_header("Step 1: Pre-Build Verifications")
    
    # Check bundled database
    bundled_db = os.path.join(BASE_DIR, "db(_Bundled_).sqlite3")
    default_db = os.path.join(BASE_DIR, "db.sqlite3")
    
    if os.path.exists(bundled_db):
        print("\n" + "!" * 60)
        print("❌ STOP: Found 'db(_Bundled_).sqlite3'!")
        print("   You forgot to rename the DB to 'db.sqlite3' before building.")
        print("   Please rename 'db(_Bundled_).sqlite3' -> 'db.sqlite3' and run again.")
        print("!" * 60 + "\n")
        sys.exit(1)

    if not os.path.exists(default_db):
        print("❌ Error: 'db.sqlite3' does not exist! Please provide the database.")
        sys.exit(1)

    size_kb = os.path.getsize(default_db) // 1024
    print(f"✔ Using database: 'db.sqlite3' ({size_kb} KB)")

    # Check version file
    print(f"✔ Target Version: {get_version()}")

def clean_build():
    print_header("Cleaning Previous Build Artifacts")
    for folder in ["build"]:
        p = os.path.join(BASE_DIR, folder)
        if os.path.exists(p):
            print(f"Removing '{folder}/'...")
            shutil.rmtree(p, ignore_errors=True)
    print("✔ Clean complete.")
 
def build_manage():
    print_header("Step 2: Building 'manage' Backend Executable")
    cmd = [sys.executable, "-m", "PyInstaller", "manage.spec", "--noconfirm"]
    run_cmd(cmd, "PyInstaller manage.spec")

def build_ipoutility():
    print_header("Step 3: Building 'IPOUtility' Desktop Launcher")
    manage_bin = "dist/manage.exe" if sys.platform == "win32" or os.path.exists("dist/manage.exe") else "dist/manage"
    if not os.path.exists(manage_bin):
        print(f"❌ Error: Expected manage binary at '{manage_bin}', but it was not found.")
        sys.exit(1)
        
    cmd = [sys.executable, "-m", "PyInstaller", "IPOUtility.spec", "--noconfirm"]
    run_cmd(cmd, "PyInstaller IPOUtility.spec")

    # Create versioned copy: IPOUtility-v<version>.exe
    version = get_version()
    ext = ".exe" if sys.platform == "win32" or os.path.exists("dist/IPOUtility.exe") else ""
    src = os.path.join(BASE_DIR, "dist", f"IPOUtility{ext}")
    dest = os.path.join(BASE_DIR, "dist", f"IPOUtility-v{version}{ext}")
    
    if os.path.exists(src):
        shutil.copy2(src, dest)
        print(f"✔ Created versioned binary: {os.path.basename(dest)}")

def verify_output():
    print_header("Build Summary")
    dist_dir = os.path.join(BASE_DIR, "dist")
    if os.path.exists(dist_dir):
        files = os.listdir(dist_dir)
        print("Generated files in 'dist/':")
        for f in sorted(files):
            fp = os.path.join(dist_dir, f)
            size_mb = os.path.getsize(fp) / (1024 * 1024)
            print(f"  • {f} ({size_mb:.2f} MB)")
    print("\n🎉 All binaries built successfully!")

def main():
    if "--clean" in sys.argv:
        clean_build()
    
    ask_user_confirmations()
    verify_files()
    build_manage()
    build_ipoutility()
    verify_output()

if __name__ == "__main__":
    main()
