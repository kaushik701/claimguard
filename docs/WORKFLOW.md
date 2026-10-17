# How ClaimGuard works (plain language)

Use this to explain the project to anyone in two minutes.

## In one line
You give ClaimGuard a product listing, a social caption or a photo of a pack. It finds every marketing claim,
checks each one against five official Indian advertising rulebooks, and tells you which claims are risky, which
rule (with page number) they may break, and how to reword them. A person always makes the final call.

## The rulebooks it reads
ASCI Code and Guidelines book, ASCI Influencer guidelines, ASCI Green-claims guidelines, the CCPA Greenwashing
guidelines (a scanned document, read with OCR), and the FSSAI Advertising and Claims Regulations.

## Step by step

**Stage 0. Learn the rulebooks (done once, repeated when a rulebook changes)**
1. Read every page. Typed pages are read directly; scanned pages are read with OCR; picture pages (infographics)
   are read with OCR and an AI vision model. Pages in Hindi legacy fonts are set aside.
2. Split the text into numbered clauses, exactly as the rulebook numbers them, and remember the page.
3. Tag each clause with what it is about (green claims, comparisons, food health claims, influencer disclosure…).
4. Build a search index so the right clause can be found by exact words and by meaning.

**Stage 1. Read the input**
- Text is cleaned; a pack photo is read with OCR and the vision model so claims printed on the pack count too.

**Stage 2. Find the claims**
- An AI model lists every claim, quoting it exactly ("Kills 99.9% germs", "eco-friendly"). One sentence can hold
  several claims. A simple rule-based finder runs too, as a safety net, so obvious claims are never missed.

**Stage 3. Find the rules for each claim**
- For each claim, search the rulebooks by exact words and by meaning, keep the best candidates, and let the AI
  pick the five most relevant clauses.

**Stage 4. Judge**
- The AI decides high / medium / low risk using a written policy, explains why in one sentence, quotes the
  clause, and suggests compliant wording with blanks for facts it doesn't know (study name, year).

**Stage 5. Check the AI's work**
- Code checks that the quoted rule text really exists in that clause and that the claim really exists in the
  input. If not, the warning is thrown away. Then a second AI checks whether the rule actually applies; it can
  only lower a warning, never raise it.

**Stage 6. Show and review**
- The reviewer sees the input with risky claims highlighted, the rule quote with its page, the suggested wording,
  and buttons: accept, dismiss, change risk, escalate.

**Stage 7. Learn**
- Every review decision is saved. Similar past decisions are shown to the AI as examples next time; rules that
  reviewers often dismiss get lower confidence; the scores on the evaluation page update. Nothing changes the live
  system until it passes the fixed test set.

## Other things you can do
- **Pre-flight**: agencies and creators check a draft before publishing and get a verdict.
- **Ask the Guidelines**: ask a question ("Can I say 'eco-friendly' if only the bottle is recycled?") and get an
  answer quoted from the rulebooks with page numbers, or "the rulebooks don't cover this".
- **Portfolio**: see where risk sits across all audited listings.
- **Knowledge explorer**: browse every clause with the original PDF page beside it.
- **Evaluation**: see how accurate the system is, honestly.
