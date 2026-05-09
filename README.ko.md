# generate_article_figure

> [English README](README.md)

생물·화학 **논문용 figure 생성 AI 에이전트**. 자연어 프롬프트를 편집 가능한 figure로 변환하고 SVG / PPTX / PNG로 export합니다.

세 가지 렌더링 path 사이를 자동 라우팅:

| Path | 백엔드 | 적합한 figure 유형 | 출력 |
|------|--------|---------------------|------|
| **A** — Vector schematic | Gemini 텍스트 → SVG (큐레이션된 bio symbol library 사용) | pathway, signaling cascade, flowchart, mechanism diagram | `image/svg+xml` |
| **B** — Chemistry structure | Gemini 추출 → RDKit → SVG | 분자, 약물, 대사물질, 원자 단위 구조 | `image/svg+xml` |
| **C** — Raster illustration | Gemini Image (Nano Banana 2 / `gemini-3.1-flash-image-preview`) | BioRender 스타일 세포·해부도·다세포 figure | `image/jpeg` |

Path C 출력은 **자연어 reprompt** 로 편집 가능 ("우상단 중복된 T cell 제거해줘"). Path A 출력은 OOXML `<asvg:svgBlip>` 임베드로 PowerPoint에서 native 도형으로 분해 가능 (우클릭 → "Convert to Shape").

## 상태

**v1, 6개 목표 기능 모두 구현 완료**:

| # | 기능 | 상태 |
|---|------|------|
| 1 | Text-to-image schematic | ✅ Path A + B + C 자동 라우팅 |
| 2 | Editable labels | ✅ Path C inpaint instruction으로 |
| 3 | Redrawable parts | ✅ Path C inpaint (mask 또는 instruction) |
| 4 | Background removable | ⏸ 보류 — Path C 출력이 이미 흰 배경 |
| 5 | Vectorize into slide (PPTX) | ✅ raster용 L1 picture, vector용 L2 SVG-embedded (Convert to Shape 동작) |
| 6 | SVG vectorization | ✅ Path A·B에서 직접 다운로드 |

mocked 테스트 149개 + live 통합 테스트 4개 (router 11/11, Path A live, Path C live, Path B aspirin live, inpaint live). 커버리지 87%.

## 셋업

Python 3.12 필요 (`.python-version`로 고정). [uv](https://docs.astral.sh/uv/)로 설치:

```bash
uv sync
cp .env.example .env  # GOOGLE_API_KEY 입력
```

## 실행

```bash
uv run uvicorn app.main:app --port 8000
```

Gradio UI: [http://localhost:8000/ui](http://localhost:8000/ui)

REST API:
- `POST /generate` — `{"prompt": "...", "figure_kind": "auto|vector|raster"}` → `{session_id, artifact, kind, routing_reason}`
- `POST /edit/{session_id}` — `{"instruction": "...", "mask": "<base64 PNG>?"}` → `{session_id, artifact, kind, revision}`
- `GET /export/{session_id}/svg` — SVG 세션만
- `GET /export/{session_id}/pptx` — 양쪽 (raster는 L1 picture, vector는 L2 SVG-embedded)
- `GET /export/{session_id}/image` — raster 세션만
- `GET /health`

## 테스트

```bash
uv run pytest                                           # mocked 149개
uv run pytest --cov=app --cov-report=term-missing
uv run pytest --run-live                                # 약 $0.13 Gemini 비용 발생
```

## 아키텍처

```
┌──────────────────────────────────────────────────────────────────┐
│  GRADIO UI (/ui에 마운트)                                          │
└─────────────┬────────────────────────────────────────────────────┘
              │
┌─────────────▼────────────────────────────────────────────────────┐
│  FastAPI app                                                      │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  Orchestrator                                            │    │
│  │  router.decide() → A | B | C                             │    │
│  │  → 적절한 tool로 dispatch                                  │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                   │
│  Tools:                                                           │
│   ├── vector_schematic  Path A: Gemini text + symbol library     │
│   ├── molecule          Path B: Gemini 추출 + RDKit              │
│   ├── raster_illustration  Path C: Gemini Image (Nano Banana 2)  │
│   ├── inpaint           Path C 편집: mask 또는 자연어              │
│   ├── export            SVG / PPTX (L1) / image                  │
│   └── export_svg_pptx   PPTX (L2) — asvg:svgBlip로 SVG 임베드     │
│                                                                   │
│  Session store: 인메모리, TTL 만료                                  │
│  Gemini client: 비동기 wrapper (retry / structured output 지원)    │
└───────────────────────────────────────────────────────────────────┘
```

`docs/progress/INDEX.md` 에 단계별 개발 로그 인덱스, `docs/progress/*.md` 에 각 단계 상세 구현 노트.

## 알려진 한계

- **Path A 라벨 위치**: Gemini가 가끔 라벨을 미세하게 겹쳐 배치 (예: 영역 라벨이 요소 가장자리에 닿음). 심볼 라이브러리 + 강화된 system prompt로 완화했지만 완전 해결은 아님.
- **Path C는 PNG가 아닌 JPEG**: `gemini-3.1-flash-image-preview`가 기본적으로 JPEG 반환. MIME은 자동 감지되어 data URI와 export에 정확히 반영.
- **Background removal 보류**: 원래 스펙의 #4 기능. Path C 출력이 실질적으로 이미 흰 배경이라 격차가 작음. 후보 라이브러리: `rembg` (U2Net).
- **PowerPoint 2016 미만**: L2 PPTX (SVG 임베드) 는 구버전 PowerPoint에서 1×1 placeholder PNG로 fallback. 모던 PowerPoint (Mac/Windows 2016+) 에서 SVG 렌더 + Convert to Shape 동작.
- **Frontend는 Gradio MVP**: 원래 계획은 Next.js + Konva (lasso 선택, 라벨 드래그 같은 풍부한 캔버스 편집). Gradio로 dogfooding 루프는 커버.

## 비용

개발 중 누적 live API 비용: **약 $0.13**.

요청당 비용:
- Path A 생성: ~$0.0001 (text) — 무시 가능
- Path B 생성: ~$0.0001 (text) + RDKit/PubChem 무료 — 무시 가능
- Path C 생성: ~$0.04 (image)
- Inpainting: ~$0.04 (image edit)
- Routing: 요청당 ~$0.0001

## 라이선스

MIT — [LICENSE](LICENSE) 참조.
