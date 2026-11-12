# Answer-first content {#answer-first}

Answer engines (Google featured snippets, AI Overviews, ChatGPT, Perplexity) quote **the passage right under a question**. Make that passage quotable:

1. **Question heading:** an `<h2>`/`<h3>` phrased the way people ask it ("How much does X cost?").
2. **Direct answer:** the very next element is a 40–60 word paragraph that answers it completely on its own. Start with the answer, not with context ("X costs $49/month for…", not "Pricing is something many people…").
3. **Then the detail:** lists, tables, examples, caveats.
4. **One question per page section;** one main topic per page.
5. **Facts beat adjectives:** numbers, names, dates and specifics get cited; "best-in-class" doesn't.
6. **Mark it up:** if the page has several visible Q&As, add `FAQPage` JSON-LD (see `schema.md`) with the *same* text.

## Rewriting rules for the agent
- Use only facts already on the page or in the repo. If the answer needs a fact you don't have, ask the user.
- Keep the site's tone and terminology.
- Show the proposed paragraph(s) to the user before applying.
- Don't turn every heading into a question; do it only where users actually ask that question (e.g. from `seo.striking_queries`).
