#!/usr/bin/env python3
"""
Generate Dash docset for Requests library from Sphinx HTML documentation.
"""

import os
import re
import sqlite3
import shutil
import sys
from pathlib import Path
from bs4 import BeautifulSoup


def create_docset_structure(docset_path: Path):
    """Create the docset directory structure."""
    resources_path = docset_path / "Contents" / "Resources"
    documents_path = resources_path / "documents"

    resources_path.mkdir(parents=True, exist_ok=True)
    documents_path.mkdir(parents=True, exist_ok=True)

    # Create Info.plist
    info_plist = docset_path / "Contents" / "Info.plist"
    info_plist.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>English</string>
    <key>CFBundleIdentifier</key>
    <string>com.kapeli.docset.requests</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>Requests</string>
    <key>CFBundlePackageType</key>
    <string>DOCS</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>DashDocSetFamily</key>
    <string>python</string>
    <key>DocSetPublisherIdentifier</key>
    <string>com.kapeli</string>
    <key>DocSetPublisherName</key>
    <string>Requests</string>
    <key>DocSetPresentationURL</key>
    <string>https://docs.python-requests.org/</string>
    <key>DocSetProviderName</key>
    <string>psf</string>
    <key>DocSetSkipIndex</key>
    <true/>
    <key>DocSetVersionString</key>
    <string>1.0</string>
    <key>IsJavaScriptEnabled</key>
    <true/>
    <key>NSHumanReadableCopyright</key>
    <string>Copyright 2012-2023 Kenneth Reitz and contributors.</string>
</dict>
</plist>
""")


def create_sqlite_index(db_path: Path):
    """Create the SQLite index for the docset."""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("""CREATE TABLE IF NOT EXISTS searchIndex(
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        path TEXT NOT NULL
    )""")

    cursor.execute("""CREATE UNIQUE INDEX IF NOT EXISTS anchor ON searchIndex(
        name, type, path
    )""")

    conn.commit()
    conn.close()


def clean_name(name: str) -> str:
    """Clean up the name by removing unwanted prefixes."""
    # Remove common prefixes
    prefixes = [
        "requests.",
        "requests.api.",
        "requests.auth.",
        "requests.cookies.",
        "requests.exceptions.",
        "requests.hooks.",
        "requests.models.",
        "requests.sessions.",
        "requests.status_codes.",
        "requests.structures.",
        "requests.utils.",
    ]

    for prefix in prefixes:
        if name.startswith(prefix):
            name = name[len(prefix) :]

    return name


def get_entry_type(classes_str: str) -> str | None:
    """Determine entry type from class string."""
    classes_lower = classes_str.lower()

    if (
        "sig-method" in classes_str
        or "meth" in classes_lower
        or "method" in classes_lower
    ):
        return "Method"
    if (
        "sig-function" in classes_str
        or "func" in classes_lower
        or "function" in classes_lower
    ):
        return "Function"
    if "sig-class" in classes_str or "class" in classes_lower:
        return "Class"
    if (
        "sig-attr" in classes_str
        or "attr" in classes_lower
        or "attribute" in classes_lower
    ):
        return "Attribute"

    return None


def extract_entries(html_file: Path) -> list:
    """Extract documentation entries from HTML file using BeautifulSoup."""
    entries = []

    try:
        html_content = html_file.read_text(encoding="utf-8")
        soup = BeautifulSoup(html_content, "lxml")

        # Find all elements with id that starts with requests.
        for elem in soup.find_all(id=True):
            elem_id = elem.get("id", "")

            # Only process requests-related IDs
            if not elem_id.startswith("requests."):
                continue

            # Get classes from element and its parent
            classes_str = elem.get("class", "")
            if isinstance(classes_str, list):
                classes_str = " ".join(classes_str)

            # Also check parent for type hints
            parent = elem.parent
            if parent:
                parent_classes = parent.get("class", "")
                if isinstance(parent_classes, list):
                    parent_classes = " ".join(parent_classes)
                classes_str = classes_str + " " + parent_classes

            entry_type = get_entry_type(classes_str)

            if not entry_type:
                # Try to infer from element name
                if elem.name in ["dt", "th"]:
                    entry_type = get_entry_type(classes_str)

            if not entry_type:
                continue

            # Get the name - extract just the last part
            name = elem_id.split(".")[-1]
            name = clean_name(name)

            if not name:
                continue

            entry = {
                "name": name,
                "type": entry_type,
                "path": html_file.name + "#" + elem_id,
            }
            entries.append(entry)

        # Debug: print sample
        if entries:
            print(f"  Found {len(entries)} entries in {html_file.name}")
            for e in entries[:3]:
                print(f"    - {e['name']} ({e['type']})")

    except Exception as e:
        print(f"Error processing {html_file}: {e}", file=sys.stderr)

    return entries


def copy_html_files(src_dir: Path, dst_dir: Path):
    """Copy HTML files to the documents directory."""
    for html_file in src_dir.glob("*.html"):
        if not html_file.name.startswith("search") and not html_file.name.startswith(
            "genindex"
        ):
            shutil.copy2(html_file, dst_dir / html_file.name)


def generate_docset(
    html_dir: Path, docset_name: str = "Requests.docset", version: str = ""
):
    """Generate the docset from HTML documentation."""
    docset_path = Path.cwd() / docset_name

    if docset_path.exists():
        shutil.rmtree(docset_path)

    print(f"Creating docset at {docset_path}")

    # Create structure
    create_docset_structure(docset_path)

    # Create SQLite index
    db_path = docset_path / "Contents" / "Resources" / "docSet.dsidx"
    create_sqlite_index(db_path)

    # Copy HTML files
    documents_path = docset_path / "Contents" / "Resources" / "documents"
    copy_html_files(html_dir, documents_path)

    # Extract entries and populate database
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    all_entries = []
    html_files = list(html_dir.glob("*.html"))
    print(f"Processing {len(html_files)} HTML files...")

    for html_file in html_files:
        entries = extract_entries(html_file)
        all_entries.extend(entries)

    # Insert entries into database
    for entry in all_entries:
        cursor.execute(
            "INSERT OR IGNORE INTO searchIndex (name, type, path) VALUES (?, ?, ?)",
            (entry["name"], entry["type"], entry["path"]),
        )

    conn.commit()
    conn.close()

    print(f"Generated {len(all_entries)} entries in docset")

    # Create tgz archive using subprocess tar
    tgz_path = Path.cwd() / f"{docset_name}.tgz"

    # Use tar command directly to avoid Python tarfile issues
    import subprocess

    docset_parent = docset_path.parent
    docset_relative = docset_path.name

    result = subprocess.run(
        ["tar", "-czf", str(tgz_path), "-C", str(docset_parent), docset_relative],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"Error creating tar: {result.stderr}", file=sys.stderr)
        # Fallback to Python tarfile
        import tarfile

        with tarfile.open(tgz_path, "w:gz") as tar:
            for root, dirs, files in os.walk(docset_path):
                for file in files:
                    if file != ".DS_Store":
                        file_path = Path(root) / file
                        arc_path = file_path.relative_to(docset_path.parent)
                        tar.add(file_path, arcname=str(arc_path))

    print(f"Created {tgz_path}")

    # Clean up docset directory
    shutil.rmtree(docset_path)

    return tgz_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate Dash docset for Requests")
    parser.add_argument(
        "--html-dir", default="_html", help="Directory containing HTML documentation"
    )
    parser.add_argument(
        "--docset-name", default="Requests.docset", help="Name of the docset"
    )
    parser.add_argument("--version", default="", help="Version string for the docset")

    args = parser.parse_args()

    html_dir = Path(args.html_dir)
    if not html_dir.exists():
        print(f"Error: HTML directory {html_dir} does not exist")
        exit(1)

    generate_docset(html_dir, args.docset_name, args.version)
