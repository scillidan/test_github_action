#!/usr/bin/env python3
"""
Generate Dash docset for Requests library from Sphinx HTML documentation.
"""

import os
import re
import sqlite3
import shutil
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
    # Remove common prefixes like 'requests.', 'requests.api.', etc.
    prefixes_to_remove = [
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

    for prefix in prefixes_to_remove:
        if name.startswith(prefix):
            name = name[len(prefix) :]

    return name


def extract_entries(html_file: Path) -> list:
    """Extract documentation entries from HTML file using BeautifulSoup."""
    entries = []

    try:
        html_content = html_file.read_text(encoding="utf-8")
        soup = BeautifulSoup(html_content, "html.parser")

        # Find all method/class/function definitions
        # Look for dt elements with id attributes (Sphinx format)
        for dt in soup.find_all("dt"):
            elem_id = dt.get("id", "")
            if not elem_id:
                continue

            # Determine the type
            if "class" in dt.attrs:
                classes = dt.attrs["class"]
                if "method" in classes:
                    entry_type = "Method"
                elif "class" in classes:
                    entry_type = "Class"
                elif "function" in classes:
                    entry_type = "Function"
                elif "attribute" in classes:
                    entry_type = "Attribute"
                else:
                    continue
            else:
                continue

            # Get the name - clean up the ID
            name = elem_id.split(".")[-1]
            name = clean_name(name)

            # Get the description from the next dd
            dd = dt.find_next_sibling("dd")
            desc = ""
            if dd:
                desc = dd.get_text(strip=True)[:200]

            # Create the entry
            entry = {
                "name": name,
                "type": entry_type,
                "path": html_file.name + "#" + elem_id,
                "desc": desc,
            }
            entries.append(entry)

    except Exception as e:
        print(f"Error processing {html_file}: {e}")

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
    for html_file in html_dir.glob("*.html"):
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

    # Create tgz archive
    import tarfile

    tgz_path = Path.cwd() / f"{docset_name}.tgz"
    with tarfile.open(tgz_path, "w:gz") as tar:
        tar.add(
            docset_path, arcname=docset_name, exclude=lambda x: x.name == ".DS_Store"
        )

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
