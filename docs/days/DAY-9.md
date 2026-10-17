# Day 9: Hardening and deploy

Read first: CLAUDE.md, docs/BUILD_PLAN.md, docs/PROGRESS.md. Plan, wait for OK, build, test, update PROGRESS.md.

## Claude Code
1. Security: injection suite, max input size, upload type checks, rate limiting per IP in public mode,
   `public_demo` blocks real uploads and shows fictional samples only.
2. Dockerfile (CPU; KB built at image build time or downloaded artefacts), deploy to Hugging Face Spaces /
   Render; secrets via platform env.
3. README: what it is, architecture diagram, how to run, results table, limits, not-legal-advice notice.
## Antigravity
Responsive and accessibility pass (390 px, keyboard, focus, contrast), empty/loading/error states on every
screen, deploy frontend (Vercel or GitHub Pages) pointing at the backend URL.
## Done when
Public URL works on a phone; a 5-minute demo video script in docs/DEMO_SCRIPT.md; PROGRESS.md complete.
