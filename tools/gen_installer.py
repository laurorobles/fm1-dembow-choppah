#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
"""Generate the 1-click Web MIDI installer (site/install/index.html) matching original CHOPPAH.

When GitHub Actions runs a release (.github/workflows/release.yml -> pages.yml), it builds
choppah-<VERSION>.fwsc and runs base/tools/make_site.py + tools/site_style.py automatically.
This script lets you generate the exact same installer locally (without needing the compiled .fwsc yet,
or using one in app/build/ if present).
"""
import argparse
import hashlib
import json
import re
import shutil
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "base"
APP = ROOT / "app"
sys.path.insert(0, str(BASE / "tools"))
sys.path.insert(0, str(ROOT / "tools"))

import make_site as ms
import site_style as ss


def build_installer(out: Path, version: str, pkg_path: Path | None) -> None:
    if out.exists():
        shutil.rmtree(out)
    (out / "install").mkdir(parents=True)
    (out / "firmware").mkdir(parents=True)

    conf = tomllib.loads((APP / "fm1.toml").read_text(encoding="utf-8"))
    pkg_name = pkg_path.name if pkg_path else f"{conf['name'].lower()}-{version}.fwsc"
    if pkg_path and pkg_path.exists():
        shutil.copy(pkg_path, out / "firmware" / pkg_name)

    boot = BASE / "web" / "m-bootloader" / f"fm1-uboot-{ms.MBOOT_VERSION}.fwsc"
    boot_name = f"m-bootloader-{ms.MBOOT_VERSION}.fwsc"
    shutil.copy(boot, out / "firmware" / boot_name)
    shutil.copy(BASE / "web" / "m-bootloader" / "LICENSE", out / "firmware" / "m-bootloader-LICENSE.txt")
    for lic in sorted((BASE / "LICENSES").glob("*.txt")):
        shutil.copy(lic, out / "firmware" / lic.name)

    html = (BASE / "web" / "installer.html").read_text(encoding="utf-8")
    lib = "\n".join(
        ms.strip_module((BASE / "web" / f).read_text(encoding="utf-8"))
        for f in ("fm1ports.js", "fm1pkg.js", "fm1ota.js")
    )
    meta = json.dumps({
        "version": version,
        "product": conf["usb_product"],
        "pkg": "../firmware/" + pkg_name,
        "backup": bool(conf.get("backup")),
        "res": None,
        "boot": {
            "pkg": "../firmware/" + boot_name,
            "version": ms.MBOOT_VERSION,
            "sha256": hashlib.sha256(boot.read_bytes()).hexdigest(),
        },
    })

    repo = conf.get("repo", "")
    credits = conf.get("credits", "")
    for key, val in (
        ("RES", conf.get("resources_what", "{{NAME}}'s data")),
        ("RES_JA", conf.get("resources_what_ja", "{{NAME}} のデータ")),
        ("NAME", conf["name"]),
        ("REPO", repo),
        ("REPO_SHORT", re.sub(r"^https?://", "", repo)),
        ("LICENSE", conf.get("licence", "MPL-2.0")),
        ("CREDITS", " " + credits if credits else ""),
    ):
        html = html.replace("{{" + key + "}}", val)

    app_js = (APP / conf["install_app"]).read_text(encoding="utf-8") if conf.get("install_app") else "null"
    (out / "install" / "index.html").write_text(
        html.replace("/*LIB*/", lib).replace("/*META*/", meta).replace("/*APP*/", app_js),
        encoding="utf-8",
    )

    # Apply CHOPPAH's dark amber styling and header
    shutil.copy(APP / "site" / "site.css", out / "site.css")
    ss.install(out)
    (out / ".nojekyll").write_text("", encoding="utf-8")
    print(f"Generated 1-click installer at: {out / 'install' / 'index.html'}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--version", default=(ROOT / "VERSION").read_text(encoding="utf-8").strip())
    ap.add_argument("--pkg", type=Path, default=None, help="Optional compiled .fwsc package")
    ap.add_argument("-o", "--out", type=Path, default=ROOT / "site")
    args = ap.parse_args()
    build_installer(args.out, args.version, args.pkg)


if __name__ == "__main__":
    main()
