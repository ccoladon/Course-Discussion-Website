## What this does

Adds `min-h-20` (minimum height 80px) to comment `article` elements in the left-hand sidebar chat.

## Problem it solves

When hovering over a comment, the reply/pin/delete/report links appear, which previously changed the height of the comment box and caused the UI to feel jumpy as elements shifted under the pointer. With `min-h-20`, the comment container always has enough reserved vertical space, so the links appear within the existing height without displacing other comments or requiring the page to reflow.

## How it works

- The `article` element now has `min-h-20` Tailwind class
- This reserves ~80px of minimum height for the comment
- On hover, the action links (Reply, Mark answered, Pin, Delete, Report) fade in via `group-hover:flex`
- Since the container already has sufficient height, there is **no layout shift** — the page doesn't jump
- The hover experience is now smooth and stable, especially on laptops with limited screen real estate

## Linked issue

See the related concern: [Issue #3: Comment hover reveals action links causing jumpy UI](https://github.com/ccoladon/Course-Discussion-Website/issues/3)

## Demo

The website is running at http://localhost:8000/login/. Sign in as `alice@demo.edu` (student) or `prof@demo.edu` (professor) with OTP code from the server log. Try hovering over comments in the chat — the action links should appear without causing the page to shift.