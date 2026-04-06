# AGENTS.md

Before doing anything else, read `README.md` in full. It is the source of truth for the core pattern (Andrej Karpathy's gist) and the spirit of this project.

This repo is building that idea locally-first, with one important emphasis:

- The **main interface** is a **CLI AI coding agent** (Codex / Claude Code style) with full local filesystem access.
- The agent should be able to read, write, edit markdown, and run bash/python tools as needed.
- The user interacts with the wiki through natural language conversation, not through a custom app UI.

## What this project is trying to do

There are two conceptual interaction modes, but in practice they blend into one organic conversation:

1. **Inputting new info**
2. **Q&A over the wiki**

Everything runs locally.

### 1) Inputting new info (happy path)

User sits down and says what they want to add in natural language. Could be:

- a psychologist logging therapy session notes and reflections,
- someone prepping for SWE interviews, logging reading progress, LeetCode practice, confusions, breakthroughs, anxiety notes, etc.

After user input, Karpathy-style wiki maintenance should happen *automatically*: summarize, file, cross-link, update related pages, keep the knowledge base coherent.

### 2) Q&A over the wiki

User asks a natural-language question. Agent traverses/searches/matches the wiki, loads the right context, and answers with grounded synthesis.

Q&A and ingest are not rigidly separated; either can pivot into the other at any point. It's one continuous conversation with the user.

## Retrieval and traversal are first-class

Because this is conversational and iterative, the agent must be very good at:

- traversal,
- retrieval,
- searching,
- matching,
- and selecting context efficiently.

## YAML frontmatter is a core primitive

Treat YAML frontmatter as a first-class driver of the system.

Even though `index.md` is useful, think of it as optional / derivable. In many cases it is a cached view over frontmatter-query capability.

Convention: **every markdown file should include YAML frontmatter** following this interface:

```yaml
---
title: string
summary: string
keywords: array[string]
created: yyyy-mm-dd
updated: yyyy-mm-dd
---
```

Some fields can be inferred/automated; some require LLM judgment. Keep them in mind both for retrieval and when modifying docs. Always remember updating them. They should represent the current snapshot of the file. No drift.

### Block/Phrase-level Metadata

Sections, paragraphs and single phrases can and should have metadata when useful.
Documents are changed many times over their lifetime. if a paragraph was added or moodified in a significant wat, an `added::yy-mm-dd` or `updated::yy-mm-dd` directive should be attached underneath it. 
This helps you and the user to mentally build a chronologically-directed knowledge graph, resolve contradictions, and give proper weight to the various notions in the wiki.

## CLI helper mental model (`wq.py`)
 
You have a CLI tool called `wq.py`.

- It loads frontmatter from all wiki markdown files.
- It builds an in-memory SQLite view.
- It accepts a limited `SELECT`-only SQL subset (with a constrained operator set).
- It prints results to stdout.

This is why `index.md` is a convenience, not the foundation: many index-like views can be generated on demand via one query.

## Harness engineering > prompt engineering

Use a harness mindset (environment design), not prompt micromanagement.

In this project, harness = setting the agent up with the right structures and automations so it can succeed repeatedly.

Three mechanisms:

1. **Skills** (progressive disclosure; load domain-specific docs/tools just-in-time)
2. **Git hooks**
   - pre-commit guard for invalid YAML frontmatter
   - automatic maintenance of `created` / `updated` fields from file attributes + policy
3. **This `AGENTS.md` file**
   - sets expectations
   - tells future agents to read `README.md`
   - captures local operating conventions

## Flow guidance (soft-formalized from README)

Prefer simple instruction-level behavior over heavy orchestration code when possible.

### Input New Info

When user provides new material:

- ingest content,
- extract key claims/events/entities,
- write/update relevant wiki pages,
- maintain links and consistency,
- update any lightweight navigation artifacts if present,
- preserve chronology where needed.

### Q&A over Wiki

When user asks:

- find relevant pages quickly,
- read selectively,
- synthesize an answer grounded in current wiki state,
- when useful, save durable results back into wiki pages.

## Only entrypoint

Primary UX is:

- user starts an interactive CLI agent,
- user chats naturally,
- agent decides and executes local actions autonomously.

No separate orchestrator layer is required beyond pragmatic CLI helpers.

## Tone / posture

Talk to the user like a skilled teammate. Be direct, natural, collaborative. Avoid bossy procedural voice unless safety/precision requires it.