# Phase 8 Roadmap

Phase 8 focuses on turning SnapBack from a recap tool into a full lecture recovery and study companion.

## Milestone 1: Study Outputs

Goal: transform completed lectures into revision materials that students can use immediately after class.

Scope:
- `POST /study/pack` backend endpoint
- AI-generated study pack with:
  - lecture outline
  - flashcards
  - quiz questions with explanations
  - review priorities
- Zoom-style panel UI for generating and reviewing study packs

Status:
- In progress
- Initial implementation included in this branch

## Milestone 2: Cross-Session Course Memory

Goal: connect multiple lecture sessions into a course timeline.

Scope:
- course entity and course-linked sessions
- week-by-week lecture summaries
- search across past sessions
- "what did we cover last class?" quick answer flow

## Milestone 3: High-Signal Lecture Detection

Goal: surface the moments that matter most for student success.

Scope:
- exam hint detection
- assignment and deadline detection
- formula / theorem / definition detection
- proactive banners and notifications

## Milestone 4: Platform-Grade Meeting Integrations

Goal: deepen the host integration quality beyond the current extension/browser wrapper layer.

Scope:
- real Zoom App integration
- stronger Google Meet side-panel experience
- Microsoft Teams meeting panel wrapper
- native host context handling

## Milestone 5: Student Review Workflows

Goal: help students go from recap to actual studying.

Scope:
- export study pack to Markdown/PDF
- spaced-repetition friendly flashcard export
- quiz mode in the panel
- "review weak areas" workflow

## Implementation Order

1. Study outputs
2. Cross-session course memory
3. High-signal lecture detection expansion
4. Real host integrations
5. Review workflows and polish
