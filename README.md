<div align="center">

# 🎨 Figure Studio

### Publication-quality bio & chem figures — from a single sentence.

Describe a pathway, a mechanism, or a cell. Get a clean, editable figure you can drop straight into a paper or slide deck.

> [한국어 README](README.ko.md)

![Figure Studio](assets/figure-studio.png)

</div>

---

## What it does

Type what you want. Pick a style. Download.

| Type | Description |
|---|---|
| 🎨 **Illustration** | A full, styled artwork — BioRender-style cells, anatomy, scenes. Refine it by just describing the change. |
| 📊 **Vector** | A clean, labeled schematic — pathways, cascades, mechanisms. Crisp arrows, balanced icons, editable in PowerPoint. |

Export to **SVG**, **PowerPoint**, or **PNG** in one click.

## Quickstart

You'll need **Python 3.12** and a **Google AI Studio API key** ([get one free](https://aistudio.google.com/apikey)).

```bash
# 1. install (uses uv — https://docs.astral.sh/uv)
uv sync

# 2. add your key
cp .env.example .env        # then paste GOOGLE_API_KEY=...

# 3. run
uv run uvicorn app.main:app --port 8000
```

Open **http://localhost:8000/ui** and start typing. That's it.

## How to use

1. **Describe** your figure in plain language — the more specific, the better.
2. **Pick** Illustration or Vector.
3. **Generate.** Watch a Vector figure improve in real time as it's refined.
4. **Step through** the versions with `◀ ▶` and keep the one you like.
5. **Download** as SVG / PowerPoint / PNG.

> 💡 Vector SVGs become **native editable shapes** in PowerPoint (right-click → *Convert to Shape*).
> Illustrations can be **refined by chat** — "remove the duplicate cell", "make the nucleus bigger".

## Tips for great figures

- Name the entities explicitly: *"EGF, EGFR, Ras, Raf, MEK, ERK"* beats *"a signaling pathway"*.
- Say the relationships: *"X activates Y"*, *"A inhibits B"*.
- Want another language in the labels? Just write the labels in that language in your prompt.
- Need a different look? Open **⚙ Models** to switch between faster and higher-quality models.

## Under the hood

Powered by Google **Gemini** (text + image). Vector figures are assembled, then put through a strict visual critic that re-checks the layout several times — arrows snap to the right edges, labels move out of the way, and icons are balanced in size — so the pieces actually fit together, not just look good alone.

## API

Prefer to call it directly? A small REST API sits under the same server:

```bash
curl -X POST localhost:8000/generate \
  -H 'content-type: application/json' \
  -d '{"prompt": "MAPK cascade: EGF → EGFR → Ras → Raf → MEK → ERK", "figure_kind": "mixed"}'
```

`figure_kind`: `mixed` (Vector) · `raster` (Illustration).
Other routes: `POST /edit/{id}`, `GET /export/{id}/{svg|pptx|image}`, `GET /health`.

## Develop & test

```bash
uv run pytest                 # full test suite
uv run pytest --run-live      # hits the live Gemini API (incurs cost)
```

## License

MIT — see [LICENSE](LICENSE).
