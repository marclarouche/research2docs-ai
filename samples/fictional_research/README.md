# Original fictional research sources

All five primary documents describe an invented Orion Archive system. They contain no real product specifications, customer deployments, benchmark results or verification claims. This README is explanatory and is not part of the five-file import.

Files: `overview.md`, `notes.txt`, `reference.html`, `workflow.docx`, `troubleshooting.pdf`.

In Project Workspace choose these five files, then **Import and index sources**. Inspect per-file warnings and results. Open Source Explorer and search `RESEARCH_READY`. Results should preserve document titles, filenames and stable passage IDs. The PDF evidence marker is on page 2. Text may appear in multiple passages or sources; retrieval is not semantic verification.

No model, embedding service or internet access is needed for import/search. Reference URLs are optional metadata only. Reimporting identical bytes under a new name skips the duplicate without changing the existing metadata. Keep original files: only extracted sections/passages and metadata are persisted by the application.

The helper `scripts/create_demo_sources.py` creates the files only when none exist. It refuses to overwrite them. Regenerated binary files may have new hashes because document container metadata can vary; stable import IDs are defined for identical input bytes and extraction/chunk settings, not for regenerated document containers.
