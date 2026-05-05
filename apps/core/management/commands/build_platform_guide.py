"""
Management command to build and cache the Platform Guide documentation.

This command reads markdown files from apps/core/docs/ and compiles them
into HTML that can be served by the platform_guide_view.
"""

import json
import os
from pathlib import Path

import markdown
from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Build the Platform Guide documentation from markdown files"

    DOCS_DIR = Path(__file__).resolve().parent.parent.parent / "docs"
    CACHE_KEY = "platform_guide_docs"
    CACHE_TIMEOUT = 60 * 60 * 24  # 24 hours

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear-cache",
            action="store_true",
            help="Clear the documentation cache without rebuilding",
        )
        parser.add_argument(
            "--output",
            type=str,
            help="Output compiled documentation to a JSON file",
        )
        parser.add_argument(
            "--page",
            type=str,
            help="Build only a specific page (filename without .md extension)",
        )

    def handle(self, *args, **options):
        if options["clear_cache"]:
            cache.delete(self.CACHE_KEY)
            self.stdout.write(self.style.SUCCESS("Documentation cache cleared"))
            return

        if not self.DOCS_DIR.exists():
            raise CommandError(f"Documentation directory not found: {self.DOCS_DIR}")

        # Get list of markdown files
        md_files = list(self.DOCS_DIR.glob("*.md"))
        if not md_files:
            raise CommandError(f"No markdown files found in {self.DOCS_DIR}")

        self.stdout.write(f"Found {len(md_files)} documentation files")

        # Build specific page or all pages
        if options["page"]:
            target_file = self.DOCS_DIR / f"{options['page']}.md"
            if not target_file.exists():
                raise CommandError(f"Page not found: {options['page']}.md")
            md_files = [target_file]

        # Compile markdown to HTML
        docs = {}
        md_converter = markdown.Markdown(
            extensions=[
                "tables",
                "fenced_code",
                "toc",
                "nl2br",
                "meta",
                "attr_list",
            ]
        )

        for md_file in md_files:
            page_name = md_file.stem  # filename without extension
            self.stdout.write(f"  Processing: {md_file.name}")

            content = md_file.read_text(encoding="utf-8")
            md_converter.reset()
            html_content = md_converter.convert(content)

            # Extract title from first h1 or filename
            title = page_name.replace("-", " ").title()
            if content.startswith("# "):
                title = content.split("\n")[0].lstrip("# ").strip()

            docs[page_name] = {
                "title": title,
                "html": html_content,
                "toc": getattr(md_converter, "toc", ""),
                "meta": getattr(md_converter, "Meta", {}),
            }

        # Build index with navigation
        if "index" in docs:
            docs["_navigation"] = self._build_navigation(md_files)

        # Store in cache
        cache.set(self.CACHE_KEY, docs, self.CACHE_TIMEOUT)
        self.stdout.write(
            self.style.SUCCESS(f"Built and cached {len(docs)} documentation pages")
        )

        # Optionally output to file
        if options["output"]:
            output_path = Path(options["output"])
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(docs, f, indent=2, ensure_ascii=False)
            self.stdout.write(self.style.SUCCESS(f"Output written to: {output_path}"))

        # Print summary
        self.stdout.write("\nDocumentation pages:")
        for page_name, page_data in sorted(docs.items()):
            if not page_name.startswith("_"):
                self.stdout.write(f"  - {page_name}: {page_data['title']}")

    def _build_navigation(self, md_files):
        """Build navigation structure from markdown files."""
        nav = []
        order = [
            "index",
            "dashboard",
            "sessions",
            "users",
            "web-design",
            "email-templates",
            "content",
        ]

        # Sort files by predefined order, then alphabetically
        sorted_files = sorted(
            md_files,
            key=lambda f: (
                order.index(f.stem) if f.stem in order else len(order),
                f.stem,
            ),
        )

        for md_file in sorted_files:
            page_name = md_file.stem
            content = md_file.read_text(encoding="utf-8")

            # Extract title
            title = page_name.replace("-", " ").title()
            if content.startswith("# "):
                title = content.split("\n")[0].lstrip("# ").strip()

            nav.append(
                {
                    "slug": page_name,
                    "title": title,
                    "is_index": page_name == "index",
                }
            )

        return nav


def get_cached_docs():
    """
    Helper function to retrieve cached documentation.
    Returns None if cache is empty (run build_platform_guide first).
    """
    return cache.get(Command.CACHE_KEY)


def get_docs_page(page_name="index"):
    """
    Helper function to retrieve a specific documentation page.
    Falls back to building from files if cache is empty.
    """
    docs = get_cached_docs()

    if not docs:
        # Build from files if cache is empty
        from django.core.management import call_command

        call_command("build_platform_guide", verbosity=0)
        docs = get_cached_docs()

    if not docs:
        return None

    return docs.get(page_name)


def get_docs_navigation():
    """
    Helper function to retrieve documentation navigation.
    """
    docs = get_cached_docs()

    if not docs:
        from django.core.management import call_command

        call_command("build_platform_guide", verbosity=0)
        docs = get_cached_docs()

    return docs.get("_navigation", []) if docs else []
