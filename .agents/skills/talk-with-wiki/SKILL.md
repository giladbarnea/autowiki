---
title: Talk With Wiki Skill
summary: Answer grounded questions over the wiki by scanning broadly for candidate pages, then diving deeply and saving durable syntheses back into the knowledge base when useful.
keywords:
  - skills
  - retrieval
  - traversal
  - question-answering
created: 2026-04-06
updated: 2026-04-06
name: talk-with-wiki
description: Answer questions and hold grounded conversations over the wiki by first mapping relevant pages, then reading them generously and synthesizing from the current state. Use when the user wants to ask, recall, discuss, compare, or reason about information already stored in the wiki.
---

# Talk With Wiki

## Goal

Help the user think with their stored knowledge, not just retrieve snippets. Answers should be grounded in the current wiki and can be saved back into it when useful.

Assume `README.md` and `AGENTS.md` define the project model. This skill operationalizes the query side of that model.

## Scan&Dive

Use a two-phase method optimized for recall.

### 1. Scan

Map the candidate set before deep reading.

Lean heavily on:

- `wq` for frontmatter-driven discovery,
- `rg` for broad grep-style keyword and phrase matching,
- `index.md` as a quick catalog if it exists,
- `log.md` when recency or evolution matters.

Prefer `wq` as the primary primitive and treat `index.md` as a convenience view, not the source of truth.

Start broad. Over-recall first. The spirit is "lots of context" rather than premature precision.

### 2. Dive

Once the relevant pages are mapped, read the selected pages generously and in full. Follow nearby pages, links, adjacent concepts, and recent history when they help the synthesis.

Selective traversal comes first; generous reading comes second.

## Answering

- Synthesize from the wiki's current state.
- Ground claims in the pages you read.
- Say plainly when the wiki is thin, contradictory, or missing something.
- When the resulting synthesis is durable, save it back into the wiki as a page or update and keep frontmatter current.
- If the question spans multiple large areas of the wiki, it is fine to use subagents for exploration and then integrate the findings.

## If the wiki is missing the answer

If the needed information is not in the wiki yet, say so plainly and pivot into ingestion of new material.
