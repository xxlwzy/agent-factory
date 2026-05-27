# Phase 3 Web Research Demo Implementation Plan

**Goal:** End-to-end demo loading `web_researcher.yaml`, fetching allowlisted HTTP content, summarizing, and writing `artifact/report.md`.

## Tasks

- [x] Spec and tests for demo LLM, summarizer, and orchestration
- [x] `WebResearchDemoLLM`, `summarize_web_content`, `run_web_research_demo`
- [x] Update specs index

Verification: `python -m pytest tests/unit -v`
