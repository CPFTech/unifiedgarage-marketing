# Marketing collateral

Two summaries of UnifiedGarage that can be handed to different audiences:

| File | Audience |
|---|---|
| `summary-developer.md` | Engineers / technical reviewers / due diligence |
| `summary-gm.md` | Dealership GMs / service managers / F&I directors / prospects |

Both have rendered PDF versions:

- `UnifiedGarage-Technical-Brief.pdf`
- `UnifiedGarage-Overview-for-GMs.pdf`

## Regenerating the PDFs after editing the markdown

```bash
pip install reportlab
python docs/build-pdfs.py
```

The script reads the `.md` files in this folder and writes the matching `.pdf` files in place. Brand chrome (yellow stripe, wordmark, page numbers, etc.) is baked into `docs/build-pdfs.py` — edit there if the look needs to change.

DejaVu Sans is used as a stand-in for Inter on Linux. On Windows / macOS the script falls back to Helvetica, which renders fine but slightly differently. If you want pixel-identical PDFs across machines, install DejaVu Sans system-wide.
