# OpenAI Images 2.6

- Source: https://openai.com/index/introducing-images-2-6/
- Announcement date: 2026-11-04 (page byline)
- Fetch date: 2026-11-09
- Also fetched the same day: [API pricing](https://developers.openai.com/api/docs/pricing), the [image generation guide](https://developers.openai.com/api/docs/guides/image-generation) (GPT Image 2.6 section), and the model pages for `gpt-image-2.6-flare` and `gpt-image-2.6-sunburst`.

The product name on the page is **Images 2.6** (API ids `gpt-image-2.6-flare` and `gpt-image-2.6-sunburst`). It is available inside Codex. It is not a separate model called "Codex Images."

## Key capabilities

Images 2.6 is in ChatGPT, Codex, and the API. The announcement's headline changes:

- **Speed.** Images generate 50% faster than before. With API quality set to low, Flare can return an image in as little as six seconds.
- **Two API models.** **Flare** is the fast option and is described as improving layout for posters, product imagery, and other professional visuals. **Sunburst** is the higher-quality option, with greater consistency across edits when quality is medium or high.
- **GIFs.** Motion from a prompt: mascots, reactions, product loops, animated storyboards. The guide documents `output_format: "gif"` on generations and edits, `frame_count` 2–16 (default 9), and `frame_duration_ms` 20–2000 (default 200).
- **Editing control in the API.** Image markup (already in ChatGPT) so a caller can mark where a change goes. A `complexity` field (`low` / `medium` / `high`) controls how much the model plans; image `quality` stays a separate knob for detail. The guide says omitting `complexity` defaults to `high`, adjusting it has no separate fee, and most edits should use low complexity. Higher complexity can add latency and unwanted changes.
- **SVG export** for websites, apps, and print. The guide: `output_format: "svg"` on generations only (not edits); the API renders a reference image, then writes static SVG (no scripts, external resources, or embedded rasters). Quality applies to that reference image. SVG is billed as the image model's reference plus whatever tokens an authoring model uses.

OpenAI also says people create about 4 billion images a week across ChatGPT, Codex, and the API.

## Quality vs prior versions

What the announcement states, without a numeric benchmark:

- 50% faster "than before." The baseline model is not named.
- Sunburst: higher-quality generation and greater consistency across edits at medium or high quality, aimed at keeping characters, products, and brand details stable.
- Flare: better layout quality for posters, product shots, and similar professional frames.
- Customer quotes, not OpenAI measurements: Picsart ("more accurate results, better character consistency, and faster generations"), Figma Weave (speed plus control while preserving character, product, or brand details), OpenArt (GIFs from a single prompt).

No Elo, win rate, or side-by-side score against `gpt-image-2`, `gpt-image-2.5`, or `gpt-image-1.5` appears on the announcement. The linked [system card](https://deploymentsafety.openai.com/chatgpt-images-2-6) was not fetched, so safety-eval numbers are unverified here.

## Pricing vs prior versions

The announcement does not print prices. It links the API pricing page. Fetched 2026-11-09, standard rates per 1M tokens:

| Model | Text in | Text in (cached) | Image in | Image in (cached) | Image out |
| --- | ---: | ---: | ---: | ---: | ---: |
| `gpt-image-2.6-flare` / `gpt-image-2.6-sunburst` | $5 | $1.25 | $8 | $2 | $30 |
| `gpt-image-2.5-flare` / `gpt-image-2.5-sunburst` | $5 | $1.25 | $8 | $2 | $30 |
| `gpt-image-2` | $5 | $1.25 | $8 | $2 | $30 |
| `gpt-image-1.5` | $5 | $1.25 | $8 | $2 | $32 |
| `gpt-image-1-mini` | $2 | $0.20 | $2.50 | $0.25 | $8 |

Flare and Sunburst share one rate card. There is no per-image sticker price. Output is $30 per 1M image tokens, same as GPT Image 2 and 2.5, and $2/1M below `gpt-image-1.5` image output ($32). `gpt-image-1.5` also lists text output at $10/1M; the 2.6 rows do not.

The guide says equal token rates do not mean equal cost per image, because token use can differ by model and quality. Its cost calculator is an interactive widget, not a static table, so per-image dollar figures for 2.6 vs 2.5 were not captured. Published per-image examples on that page are for earlier models (the guide says those tables do not apply to Sunburst or Flare). For `gpt-image-2`, square output examples there are about $0.006 (low), $0.053 (medium), and $0.211 (high). Do not treat those as 2.6 prices.

Batch: both 2.6 model pages mark `v1/batch` as not supported, and neither id is on the batch price table. GPT Image 2.5 Flare and Sunburst are, at half the standard rates ($15/1M image output). A batch workflow on 2.5 is cheaper per token than on-demand 2.6 at the same token count.

ChatGPT and Codex: available globally on all subscription tiers, desktop, mobile, and web. No consumer per-image price or quota is stated. API surface that is documented: `POST /v1/images/generations` and `POST /v1/images/edits`. The model pages mark Chat Completions, Responses, and Batch as not supported for these ids. Whether the Responses image tool accepts a 2.6 model id is unverified; the guide's worked examples still pass `gpt-image-2.5-sunburst`.

## Implications

**This repo (agterm-claude-images).** The gallery only displays images that already appear in a Claude Code transcript (pastes, `Read`, MCP screenshots). It does not call an image model, so Images 2.6 does not change install, hooks, or generation behavior. `agterm-gallery.py` already keeps `image/gif` (along with png, jpeg, and webp), so a GIF that shows up in a transcript can be saved. `image/svg+xml` is not in that allowlist. Nothing here should be switched to 2.6.

**Other image-generation workflows (not this repo).** The `codex-image` skill and app-icon / store-card / header jobs are the places this matters, once the tool actually offers the new ids (that mapping is unverified below).

- Fast layout drafts (headers, posters, product frames): `gpt-image-2.6-flare`, quality low or medium, complexity low.
- Final icons and store cards, especially multi-step edits that must keep a mark consistent: `gpt-image-2.6-sunburst` at medium or high quality. Try `output_format: "svg"` for icons and simple illustrations.
- Do not expect a lower token price than GPT Image 2.5. If a job runs on the Batch API today, leave it on 2.5 until 2.6 batch exists.
- Set `complexity` explicitly. The documented default is `high`, which the guide says can slow the call and change more than you asked.

## Unverified

- Per-image token counts and dollar cost for 2.6 vs 2.5 or vs `gpt-image-2` at a given size and quality. The official calculator did not render as a table. Third-party write-ups of those counts were not used.
- Which prior model the "50% faster" claim uses, and any quality score that is not a quote above.
- Contents of the Images 2.6 system card (not fetched).
- ChatGPT and Codex quotas, rate limits, and whether image use is metered inside a subscription.
- Whether Codex (the product) or the Codex CLI `image_gen` tool defaults to 2.6, and which model string the `codex-image` skill sends. The announcement only says Images 2.6 is available in Codex.
- Responses API image-tool support for the 2.6 ids (examples in the guide still use 2.5).
- Cached-input applicability for 2.6. The pricing footnote that limits cached rates to the Responses API names GPT Image 2 and 2.5 only.
- That a GIF or SVG produced by 2.6 displays correctly in the agterm pane. The gallery's mime allowlist was read in source; it was not run against a 2.6 file.
