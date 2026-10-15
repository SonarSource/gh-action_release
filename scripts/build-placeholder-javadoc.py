#!/usr/bin/env python3
"""Rebuild main/release/resources/placeholder-javadoc.jar byte for byte.

The jar is reproducible (fixed entry order and timestamps), so its detached signature stays valid for
every build of it. After a change, sign it with the release key:

    gpg --armor --detach-sign -o main/release/resources/placeholder-javadoc.jar.asc \
        main/release/resources/placeholder-javadoc.jar
"""
import os
import zipfile

JAR = os.path.join(os.path.dirname(__file__), "..", "main", "release", "resources", "placeholder-javadoc.jar")
FIXED_TIME = (1980, 1, 1, 0, 0, 0)
ENTRIES = {
    "META-INF/MANIFEST.MF": "Manifest-Version: 1.0\r\nCreated-By: SonarSource gh-action_release\r\n\r\n",
    "README.md": "The javadoc of this artifact is published at https://javadocs.sonarsource.org/\n",
}


def build(path):
    # Entries are stored, not deflated: the bytes then depend on this script only, not on the zlib in use
    with zipfile.ZipFile(path, "w", zipfile.ZIP_STORED) as jar:
        for name, content in ENTRIES.items():
            info = zipfile.ZipInfo(name, FIXED_TIME)
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = 0o644 << 16
            jar.writestr(info, content)


def main():
    build(JAR)
    print(f"wrote {os.path.normpath(JAR)}")


if __name__ == "__main__":
    main()
