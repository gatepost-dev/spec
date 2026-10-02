# SPDX-FileCopyrightText: 2026 The Gatepost authors
# SPDX-License-Identifier: Apache-2.0
"""Sample text, file names and messages that the check_tells tests share."""

import string

EMOJI = chr(0x1F600)
NO_BREAK_SPACE = chr(0x00A0)
E_ACUTE = chr(0x00E9)
EM_DASH = chr(0x2014)
LINE_SEPARATOR = chr(0x2028)
O_DOT_BELOW = chr(0x1ECD)
LONG_LINE = "x" * 150
# Built from two parts, so that this file passes its own to-do check.
TO_DO = "TO" + "DO"
FIX_ME = "FIX" + "ME"
# Built from two parts, so that this file passes its own skip check.
SKIP_MARKER = "check-tells: " + "allow"

KIND_BY_PATH = {
    "code": [
        "a.ts",
        "a.tsx",
        "a.mts",
        "a.cts",
        "a.js",
        "a.jsx",
        "a.mjs",
        "a.cjs",
        "a.php",
        "a.py",
        "a.go",
        "a.kt",
        "a.kts",
        "a.java",
        "a.cs",
        "a.dart",
        "a.swift",
        "a.sql",
        "a.sh",
        "a.bash",
        "a.css",
        "a.scss",
        "a.html",
        "a.astro",
        "a.vue",
        "a.svelte",
        "A.TS",
        "config.php.dist",
    ],
    "config": [
        "a.json",
        "a.yml",
        "a.yaml",
        "a.toml",
        "a.xml",
        "a.ini",
        "a.cfg",
        "a.properties",
        "a.gradle",
        "a.neon",
        "a.json5",
        "a.jsonc",
        "A.JSON",
        "phpunit.xml.dist",
        "phpstan.neon.dist",
        "phpstan.dist.neon",
        "Makefile",
        "Dockerfile",
        ".editorconfig",
        ".gitignore",
        ".gitattributes",
        ".npmrc",
    ],
    "prose": ["a.md", "a.mdx", "A.MD"],
    "catalogue": [
        "a.arb",
        "a.po",
        "a.xlf",
        "a.xliff",
        "a.strings",
        "a.stringsdict",
        "src/locales/en.json",
        "src/i18n/en.json",
        "src/l10n/en.json",
        "src/messages/en.json",
        "src/locales/yo/home.json",
        "res/values/strings.xml",
        "res/values-yo/strings.xml",
    ],
    "exempt": [
        "pnpm-lock.yaml",
        "package-lock.json",
        "yarn.lock",
        "composer.lock",
        "go.sum",
        "uv.lock",
        "poetry.lock",
        "Cargo.lock",
        "Package.resolved",
        "pubspec.lock",
        "gradle.lockfile",
        "packages.lock.json",
        "a.svg",
        "a.lock",
        "a.csv",
        "a.txt",
        "a.api",
        "a.snap",
        "a.png",
        "a.jpg",
        "a.ico",
        "src/locales/yo.txt",
    ],
    "other": ["LICENSE", "CODEOWNERS", ".gitmodules", "a.woff", "res/layout/strings.xml.bak"],
}

SIGN_OFF_LINE = "Signed-off-by: Ada Bello <ada@example.org>"
PLACEHOLDER_PARAGRAPH = (
    "Write two or three sentences of plain prose that say what this change does and why."
)
# The comment that Renovate adds at the very end of the body of its pull requests. The payload
# holds each character of base64.
BASE64 = string.ascii_letters + string.digits + "+/"
RENOVATE_COMMENT = f"<!--renovate-debug:{BASE64}==-->"


def squash(
    subject: str, body: str = "Why the change is needed.", sign_off: str = SIGN_OFF_LINE
) -> str:
    """Build a squash merge message from a title with its suffix, a body and a sign-off."""
    return f"{subject}\n\n{body}\n\n{sign_off}\n"
