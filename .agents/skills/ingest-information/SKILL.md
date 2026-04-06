---
title: Ingest Information Skill
summary: Integrate new material into the persistent wiki by traversing sources, extracting their substance, and updating the relevant markdown pages.
keywords:
  - skills
  - ingest
  - wiki-maintenance
  - traversal
created: 2026-04-06
updated: 2026-04-06
name: ingest-information
description: Integrate new material into the wiki by traversing the source, extracting the important information, and updating the relevant markdown pages, links, and lightweight navigation artifacts. Use when the user wants to add new notes, documents, transcripts, folders, reflections, or any new information to the wiki.
---

# Ingest Information

## Goal

When the user brings new material, fold it into the persistent wiki so future conversations can build on it.

Assume `README.md` and `AGENTS.md` define the core ingest behavior. This skill is the short operational reminder.

## Workflow

1. Traverse the material effectively.
2. Extract the key claims, events, entities, themes, and chronology.
3. Write new pages or update existing ones.
4. Maintain links, summaries, and consistency across touched pages.
5. Update lightweight navigation artifacts if present, such as `index.md` and `log.md`.
6. Preserve chronology where it matters.
7. Keep YAML frontmatter current on every markdown file you create or modify.

## Traversal first

Good ingestion depends on good traversal. Before editing, map what already exists in the wiki and what the new material touches. For traversal and retrieval behavior, load `talk-with-wiki`.

The user does not need to provide a perfect inventory. A rough path, source cluster, or document pointer is enough; the agent should do the discovery work.

If the source landscape is broad or scattered, it is fine to use subagents to map the terrain before integrating the final result.

## Output mindset

Treat the wiki as the compounding artifact, not the chat reply. Durable syntheses, updated entity pages, revised topic pages, explicit cross-links, and coherent chronology are the main deliverable.
