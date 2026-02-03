"""
download the documentation of 'Beautiful Soup 4' and generate a 'docset' (offline documentation) for Dash/Zeal/Velocity

based on: https://github.com/iamaziz/bs4-dash by @iamaziz (Aziz Alto)
rewritten for Python 3 by: @iNtEgraIR2021 (Petra Mirelli) 2021-2022
rewritten by MiniMax-M2.1🧙‍♂️, scillidan🤡 2026
"""

import json
import sys
import sqlite3
import re
from pathlib import Path
from pprint import pprint

from urllib.request import urlretrieve

from bs4 import BeautifulSoup as bs
import requests

docset_name = "Beautiful_Soup_4.docset"
output = docset_name + "/Contents/Resources/Documents/"

root_url = "https://www.crummy.com/software/BeautifulSoup/bs4/doc/"

p = Path(output) / Path("crummy.com/bs4/")
p.mkdir(parents=True, exist_ok=True)
output = str(p) + "/"

import shutil

shutil.copy2("assets/icon.png", docset_name + "/icon.png")
shutil.copy2("assets/icon@2x.png", docset_name + "/icon@2x.png")
print("Copied icon.png and icon@2x.png from assets/")


def get_version():
    version_url = "https://www.crummy.com/software/BeautifulSoup/bs4/doc/"
    data = str(requests.get(version_url).text).strip()
    soup = bs(data, features="html.parser")

    version_paragraph = None
    for p in soup.find_all("p"):
        if "This document covers" in p.get_text():
            version_paragraph = p
            break

    if version_paragraph:
        version_match = re.search(
            r"Beautiful Soup version\s+([\d.]+)", version_paragraph.get_text()
        )
        if version_match:
            return version_match.group(1)

    return "4.x"


def determine_type(entry_text, name=""):
    entry_lower = entry_text.lower().strip()
    name_lower = name.lower().strip() if name else ""

    if entry_lower.startswith("module") or "(module)" in entry_lower:
        return "Module"
    elif "class" in entry_lower and "exception" not in entry_lower:
        return "Class"
    elif (
        "exception" in entry_lower
        or "warning" in entry_lower
        or name_lower == "parserrejectedmarkup"
    ):
        return "Exception"
    elif "(method)" in entry_lower or " method" in entry_lower:
        return "Method"
    elif "(attribute)" in entry_lower or " attribute" in entry_lower:
        return "Attribute"
    elif (
        "(function)" in entry_lower
        or " function" in entry_lower
        or entry_lower.endswith("()")
    ):
        return "Function"
    elif (
        "constant" in entry_lower
        or entry_lower.startswith("default_")
        or entry_lower.startswith("prefix")
        or entry_lower.startswith("suffix")
        or "charset_aliases" in entry_lower
    ):
        return "Constant"
    elif entry_lower.startswith("_") and not entry_lower.endswith(")"):
        return "Attribute"
    else:
        return "Function"


def update_db(name, path, typ):
    cur.execute(
        "CREATE TABLE IF NOT EXISTS searchIndex(id INTEGER PRIMARY KEY, name TEXT, type TEXT, path TEXT);"
    )
    cur.execute("SELECT rowid FROM searchIndex WHERE path = ?", (path,))
    fetched = cur.fetchone()
    if fetched is None:
        cur.execute(
            "INSERT OR IGNORE INTO searchIndex(name, type, path) VALUES (?,?,?)",
            (name, typ, path),
        )
        print(f"DB add >> name: {name}, type: {typ}, path: {path}")

    cur.execute(
        "CREATE TABLE IF NOT EXISTS ztoken(zid INTEGER PRIMARY KEY, zname TEXT, ztype TEXT, zpath TEXT);"
    )
    cur.execute("SELECT zid FROM ztoken WHERE zpath = ?", (path,))
    fetched_ztoken = cur.fetchone()
    if fetched_ztoken is None:
        cur.execute(
            "INSERT OR IGNORE INTO ztoken(zname, ztype, zpath) VALUES (?,?,?)",
            (name, typ, path),
        )


def get_css_file(file_name):
    file_url = root_url + str(file_name)
    print(f" downloading css file {file_url}")

    content_temp = str(requests.get(file_url).text).strip()
    content_temp = re.sub(r"(?im)[\r\t\n]+", "", content_temp)

    import_pattern = re.compile(r"(?im)(\@import url\()([\'\"]+)([^\'\"]+)([\'\"]+)\)")
    import_matches = re.findall(import_pattern, content_temp)
    for import_match in import_matches:
        file_name = str(import_match[2]).strip().strip("'").strip('"')
        if len(file_name) > 0:
            content_temp += str(get_css_file("_static/" + file_name))

    content_temp = re.sub(import_pattern, "", content_temp)
    content_temp = re.sub(r"(?m)\/\*[^*]*\*+([^\/*][^*]*\*+)*\/", "", content_temp)

    while "  " in content_temp:
        content_temp = re.sub(r"(?m)( ){2}", " ", content_temp).strip()

    return content_temp


def get_js_file(file_name):
    file_url = root_url + str(file_name)
    print(f" downloading js file {file_url}")

    content_temp = str(requests.get(file_url).text).strip()
    content_temp = re.sub(r"(?im)[\r\t\n]+", "", content_temp)

    while "  " in content_temp:
        content_temp = re.sub(r"(?m)( ){2}", " ", content_temp).strip()

    return content_temp


def download_page(url, save_path):
    print(f"Downloading: {url}")
    data = str(requests.get(url).text).strip()
    soup = bs(data, features="html.parser")

    css_links = soup.select('head > link[href$=".css"]')
    if len(css_links) > 0:
        css_content = ""
        for css_link in css_links:
            css_href = str(css_link.get("href")).strip()
            if not css_href.startswith("http"):
                css_href = url.rsplit("/", 1)[0] + "/" + css_href
            css_content += get_css_file(css_href)

        if len(css_content) > 0:
            style_tag = bs(
                "<style>" + str(css_content) + "</style>", features="html.parser"
            ).style
            if css_links and css_links[0]:
                css_links[0].replace_with(style_tag)
                css_links = soup.select('head > link[href$=".css"]')
                for css_link in css_links:
                    css_link.decompose()

    js_scripts = soup.select("head > script")
    if len(js_scripts) > 0:
        js_content = ""
        for js_script in js_scripts:
            js_src = str(js_script.get("src")).strip()
            if js_src and not js_src.startswith("http"):
                js_src = url.rsplit("/", 1)[0] + "/" + js_src
            if js_src:
                js_content += get_js_file(js_src)

        if len(js_content) > 0:
            script_tag = bs(
                '<script type="text/javascript" data-url_root="./">'
                + str(js_content)
                + "</script>",
                features="html.parser",
            ).script
            if js_scripts:
                js_scripts[0].replace_with(script_tag)
                js_scripts = soup.select("head > script")
                for js_script in js_scripts:
                    if js_script.get("src") is not None:
                        js_script.decompose()

    img_tags = soup.select("img")
    for img_tag in img_tags:
        img_src = str(img_tag.get("src")).strip()
        if len(img_src.replace("None", "")) > 1:
            if not img_src.startswith("http"):
                img_src = url.rsplit("/", 1)[0] + "/" + img_src
            img_file_name = img_src.split("/")[-1]
            img_url = img_src

            print(f"downloading image '{img_url}' ")
            try:
                with open(output + img_file_name, "wb") as f:
                    f.write(requests.get(img_url).content)
                img_tag["src"] = img_file_name
            except Exception as e:
                print(f"Failed to download image: {e}")

    search_box = soup.select("#searchbox")
    if len(search_box) == 1:
        search_box[0].string = ""

    search_link = soup.select('link[rel="search"]')
    if len(search_link) == 1:
        search_link[0].decompose()

    index_link = soup.select('link[rel="index"]')
    if len(index_link) == 1:
        index_link[0].decompose()

    with open(save_path, "w+", encoding="utf-8") as fh:
        fh.write(str(soup.prettify()))

    return soup


def parse_genindex():
    genindex_url = root_url + "genindex.html"
    print(f"Parsing genindex: {genindex_url}")

    data = str(requests.get(genindex_url).text).strip()
    soup = bs(data, features="html.parser")

    index_entries = []
    seen_paths = set()

    for link in soup.select("table.indextable a[href]"):
        entry_href = link.get("href", "")
        entry_text = link.get_text().strip()

        if entry_href.startswith("api/") and "#" in entry_href:
            if entry_text.startswith("("):
                continue

            if entry_text.replace("[", "").replace("]", "").isdigit():
                continue

            if entry_href in seen_paths:
                continue
            seen_paths.add(entry_href)

            path = "crummy.com/bs4/" + entry_href

            name = entry_text
            paren_idx = entry_text.rfind("(")
            if paren_idx > 0:
                name = entry_text[:paren_idx].strip()
                name = name.rstrip(".")

            if entry_text.lower().startswith("module"):
                anchor = entry_href.split("#")[-1]
                if anchor.startswith("module-"):
                    name = anchor.replace("module-", "")

            typ = determine_type(entry_text, name)

            index_entries.append({"name": name, "type": typ, "path": path})

    print(f"Found {len(index_entries)} index entries")
    return index_entries


def add_urls():
    data = str(requests.get(root_url).text).strip()
    soup = bs(data, features="html.parser")

    css_links = soup.select('head > link[href$=".css"]')
    if len(css_links) > 0:
        css_content = ""
        for css_link in css_links:
            css_href = str(css_link.get("href")).strip()
            css_content += get_css_file(css_href)

        if len(css_content) > 0:
            css_links[0].replace_with(
                bs(
                    "<style>" + str(css_content) + "</style>", features="html.parser"
                ).style
            )
            css_links = soup.select('head > link[href$=".css"]')
            for css_link in css_links:
                css_link.decompose()

    js_scripts = soup.select("head > script")
    if len(js_scripts) > 0:
        js_content = ""
        for js_script in js_scripts:
            js_src = str(js_script.get("src")).strip()
            js_content += get_js_file(js_src)

        if len(js_content) > 0:
            js_scripts[0].replace_with(
                bs(
                    '<script type="text/javascript" id="documentation_options" data-url_root="./">'
                    + str(js_content)
                    + "</script>",
                    features="html.parser",
                ).script
            )

            js_scripts = soup.select("head > script")
            for js_script in js_scripts:
                if js_script.get("src") is not None:
                    js_script.decompose()

    img_tags = soup.select("img")
    for img_tag in img_tags:
        img_src = str(img_tag.get("src")).strip()
        if len(img_src.replace("None", "")) > 1:
            img_file_name = img_src.split("/")[-1]
            img_url = root_url + img_src

            print(f"downloading image '{img_url}' ")
            with open(output + img_file_name, "wb") as f:
                f.write(requests.get(img_url).content)

            img_tag["src"] = img_file_name

    index_link = soup.select('link[rel="index"]')
    if len(index_link) == 1:
        index_link[0].decompose()

    index_a = soup.select('a[href$="genindex.html"]')
    if len(index_a) > 0:
        for a_temp in index_a:
            a_temp.decompose()

    search_link = soup.select('link[rel="search"]')
    if len(search_link) == 1:
        search_link[0].decompose()

    search_box = soup.select("#searchbox")
    if len(search_box) == 1:
        search_box[0].string = ""

    with open(output + "index.html", "w+", encoding="utf-8") as fh:
        fh.write(str(soup.prettify()))

    api_files = set()
    entries = parse_genindex()

    for entry in entries:
        path = entry["path"]
        if "#" in path:
            api_file = path.split("#")[0]
            api_files.add(api_file)

    api_base_path = output + "api/"
    Path(api_base_path).mkdir(parents=True, exist_ok=True)

    for api_file in sorted(api_files):
        relative_path = api_file.replace("crummy.com/bs4/", "")
        save_path = output + relative_path
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)

        url = root_url + relative_path
        try:
            download_page(url, save_path)
        except Exception as e:
            print(f"Failed to download {url}: {e}")

    for entry in entries:
        update_db(entry["name"], entry["path"], entry["type"])


def add_infoplist():
    CFBundleIdentifier = "bs4"
    CFBundleName = "Beautiful Soup 4"
    DocSetPlatformFamily = "bs4"
    DashDocSetFamily = "python"

    info = """<?xml version="1.0" encoding="UTF-8"?>
<plist version="1.0">
<dict>
  <key>CFBundleIdentifier</key>
  <string>{0}</string>
  <key>CFBundleName</key>
  <string>{1}</string>
  <key>DocSetPlatformFamily</key>
  <string>{2}</string>
  <key>DashDocSetFamily</key>
  <string>{3}</string>
  <key>dashIndexFilePath</key>
  <string>www.crummy.com/software/BeautifulSoup/bs4/doc/index.html</string>
  <key>isDashDocset</key>
  <true/>
</dict>
</plist>""".format(
        CFBundleIdentifier, CFBundleName, DocSetPlatformFamily, DashDocSetFamily
    )

    with open(docset_name + "/Contents/info.plist", "w", encoding="utf-8") as fh:
        fh.write(info)


def add_meta(version):
    meta_dict = {
        "extra": {"indexFilePath": "crummy.com/bs4/index.html"},
        "name": "Beautiful Soup",
        "title": "Beautiful Soup",
        "version": version,
    }

    with open(docset_name + "/meta.json", "w+", encoding="utf-8") as fh:
        fh.write(str(json.dumps(meta_dict, indent=4)))


db = sqlite3.connect(docset_name + "/Contents/Resources/docSet.dsidx")
cur = db.cursor()

cur.execute(
    "CREATE TABLE IF NOT EXISTS searchIndex(id INTEGER PRIMARY KEY, name TEXT, type TEXT, path TEXT);"
)
cur.execute("CREATE UNIQUE INDEX anchor ON searchIndex (name, type, path);")
cur.execute(
    "CREATE TABLE IF NOT EXISTS ztoken(zid INTEGER PRIMARY KEY, zname TEXT, ztype TEXT, zpath TEXT);"
)
cur.execute("CREATE UNIQUE INDEX zanchor ON ztoken (zname, ztype, zpath);")

try:
    cur.execute("DROP TABLE searchIndex;")
    cur.execute("DROP TABLE ztoken;")
except Exception as e:
    print(e)
    cur.execute(
        "CREATE TABLE IF NOT EXISTS searchIndex(id INTEGER PRIMARY KEY, name TEXT, type TEXT, path TEXT);"
    )
    cur.execute("CREATE UNIQUE INDEX anchor ON searchIndex (name, type, path);")
    cur.execute(
        "CREATE TABLE IF NOT EXISTS ztoken(zid INTEGER PRIMARY KEY, zname TEXT, ztype TEXT, zpath TEXT);"
    )
    cur.execute("CREATE UNIQUE INDEX zanchor ON ztoken (zname, ztype, zpath);")


version = get_version()

add_urls()

add_infoplist()

add_meta(version)

db.commit()
db.close()

print("Docset generation complete!")
