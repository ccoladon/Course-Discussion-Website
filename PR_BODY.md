## What this does

Replaces the flat list of all channels with an accordion-style sidebar in the left navigation:
- Section (class) names are shown with disclosure arrows (▼)
- Channels are initially hidden under each section
- Click a section header to expand/collapse its channels
- Clicking a channel still navigates to it and closes the sidebar
- Keeps the sidebar compact with many classes while retaining full functionality

## Problem solved

Previously, with many enrolled courses, the left-hand column became excessively tall, making the site difficult to use on laptops. Now the sidebar stays compact — only section names are visible by default.

## How it works

- The sidebar renders each class name as an accordion header
- Channels (#general, #assignments, #exams, #projects, #offtopic) are hidden under each section
- Clicking a section header toggles visibility and rotates the arrow
- Clicking a channel navigates to it (sidebar closes automatically)
- The active channel still highlights with the indigo background

## Demo

The website is running at http://localhost:8000/login/. Sign in as `alice@demo.edu` (student) or `prof@demo.edu` (professor) with code `312893` from the server log.