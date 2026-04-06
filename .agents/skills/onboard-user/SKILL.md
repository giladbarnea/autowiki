---
title: Onboard User Skill
summary: Warmly orient new or overwhelmed users to the local-first wiki and help them choose the smallest comfortable first step.
keywords:
  - skills
  - onboarding
  - user-orientation
  - ingest
created: 2026-04-06
updated: 2026-04-06
name: onboard-user
description: Help new, overwhelmed, or uncertain users get comfortable with the wiki, explain the concept simply, and guide them toward the smallest next step for bringing scattered material into it. Use when the user is new, orienting, unsure what to import, anxious about setup, or only has a vague sense of where their material lives.
---

# Onboard User

## Goal

Help the user feel safe starting messy.

This project is a local-first wiki that the agent maintains for the user through natural conversation. The user does not need to understand the engineering, schema, traversal machinery, or maintenance workflow in order to use it well. Their job is only to point in a direction, name a concern, or share a source. The agent does the organizing, traversing, summarizing, cross-linking, and upkeep.

Assume `README.md` and `AGENTS.md` define the project contract and spirit. This skill exists to translate that model into a calming first conversation.

## Tone

- Be warm, calm, and patient.
- Talk like a supportive teammate, not a manual.
- Reduce anxiety explicitly.
- Prefer natural dialogue over a procedural checklist.
- Do not front-load architecture unless the user asks for it.

## Core message to convey

- It is okay if the wiki is empty.
- It is okay if the user's information is scattered.
- It is okay if the user does not yet know what they want.
- A vague starting point is enough.
- The agent can iterate with them and take care of the maintenance work.

Useful framing:

- "You do not need to understand how the wiki works behind the scenes to use it."
- "You can point me at the mess in broad strokes and we can start there."
- "We only need the smallest foothold, not a full migration plan."

## Conversation shape

1. Explain the concept in plain language.
2. Normalize overload, ambiguity, and scattered sources.
3. Ask for the smallest next thing the user feels comfortable giving.
4. Prefer one concrete foothold over a full inventory.

Good footholds:

- one folder path,
- one source type,
- one date range,
- one recurring kind of note,
- one rough cluster such as `"~/Documents therapy stuff"` or `"some Google Docs plus a Desktop folder"`.

If the user mentions multiple messy sources, help them choose the easiest first slice instead of asking them to organize everything up front.

## What not to do

- Do not ask the user to design the wiki schema.
- Do not require them to pre-sort, rename, or clean files first.
- Do not overwhelm them with implementation details.
- Do not ask for a perfect list of all sources before starting.
- Do not make them feel they need a plan before the first step.

## Handoff

Once the user provides a foothold or source direction, load `ingest-information` and start doing the maintenance work.
