# generate_article_figure

> [English README](README.md)

생물·화학 **논문용 figure 생성 AI 에이전트**. 자연어 프롬프트를 편집 가능한 figure로 변환하고 SVG / PPTX / PNG로 export합니다.

웹앱 — **Figure Studio** — 은 두 가지 결과물을 노출하고, 내부적으로는 네 개의 렌더링 path로 라우팅합니다.

| 화면 모드 | Path | 백엔드 | 적합한 figure | 출력 |
|-----------|------|--------|----------------|------|
| **Illustration** | C | Gemini Image (Nano Banana) | BioRender 스타일 세포·해부도·다세포 figure | `image/jpeg` |
| **Vector** | D (+ 내부 A, B) | Gemini 텍스트 → SVG 백본 + 생성 raster 아이콘 | pathway, cascade, hub-and-spoke, mechanism diagram | `image/svg+xml` |

내부 path (`figure_kind=auto`일 때 LLM router가 선택):

| Path | 백엔드 | 비고 |
|------|--------|------|
| **A** — Vector schematic | Gemini 텍스트 → SVG + 큐레이션 bio symbol library | ~23개 수작업 심볼 `<use>` |
| **B** — Chemistry structure | Gemini 추출 → RDKit → SVG | 원자 단위 분자; PubChemPy fallback |
| **C** — Raster illustration | Gemini Image | 자연어 reprompt로 편집 가능 |
| **D** — Mixed (Vector) | Gemini 텍스트 백본 + 엔티티별 생성 raster 아이콘 | 아이콘은 텍스트 없음, 라벨은 전부 vector |

**Illustration** 출력은 **자연어 reprompt** 로 편집 가능 ("우상단 중복된 T cell 제거해줘"). **Vector** SVG 출력은 OOXML `<asvg:svgBlip>` 임베드로 PowerPoint에서 native 도형으로 분해 가능 (우클릭 → "Convert to Shape").

## 구성 품질 (Path D)

Vector figure는 각 요소가 개별적으로만 좋은 게 아니라 **합쳐졌을 때**도 깔끔하도록 다층 방어를 거칩니다:

```
LLM 백본
  → 엄격한 vision critic ×3      (Nature/Cell 에디터 기준: 묻힌 화살표,
                                   깨진 대칭, 정렬 어긋남, 겹침)
  → arrow_clip (결정론적)        connector 끝점 → 아이콘 가장자리, 안 묻힘
  → label_declutter (결정론적)   라벨을 connector/아이콘에서 밀어냄
  → area-fill 아이콘 크기 (결정론) 같은 박스 → 같은 아이콘 면적, 균형
```

critic은 최대 3 refine pass (keep-best); 결정론적 pass들이 LLM 변동과 무관하게 화살표 부착·라벨 간격·아이콘 크기 균형을 보장합니다. UI는 각 candidate를 실시간 스트리밍하고 넘겨보며 선택하게 합니다.

## 상태

**v1 + Path D + Figure Studio UI.**

| # | 기능 | 상태 |
|---|------|------|
| 1 | Text-to-figure | ✅ Illustration + Vector (Path A/B/C/D, 자동 라우팅) |
| 2 | Editable labels | ✅ Illustration 자연어 reprompt |
| 3 | Redrawable parts | ✅ Illustration inpaint (mask 또는 instruction) |
| 4 | Background removable | ⏸ 보류 — 출력이 이미 흰 배경 |
| 5 | Vectorize into slide (PPTX) | ✅ raster L1 picture, vector L2 SVG-embedded (Convert to Shape 동작) |
| 6 | SVG vectorization | ✅ 직접 다운로드 |

mocked 테스트 276개 + live 통합 테스트 (`--run-live`).

## 셋업

Python 3.12 필요 (`.python-version`로 고정). [uv](https://docs.astral.sh/uv/)로 설치:

```bash
uv sync
cp .env.example .env  # GOOGLE_API_KEY 입력
```

기본 모델 (`.env` 또는 UI에서 요청별 override):
- 언어: `gemini-3.5-flash`
- 이미지: `gemini-3.1-flash-image-preview` (Nano Banana 2)

## 실행

```bash
uv run uvicorn app.main:app --port 8000
```

**Figure Studio**: [http://localhost:8000/ui](http://localhost:8000/ui)

### Figure Studio UI

- **두 모드**: Illustration (완성 스타일 아트워크) / Vector (라벨 달린 도식).
- **모델 선택** (⚙ Models): 언어 모델 (`3.5 Flash` / `3.1 Pro`), 이미지 모델 (`Nano Banana 2` / `Nano Banana Pro`) 요청별 변경.
- **실시간 미리보기**: Vector figure가 critic pass를 거치며 좋아지는 걸 캔버스에서 확인.
- **Candidate 네비게이션**: `◀ ▶` 로 critic candidate들을 넘겨보고 원하는 걸 다운로드.
- **Refine** (Illustration 전용): 자연어 reprompt로 이미지 편집.
- **다운로드**: SVG / PowerPoint / PNG, figure 종류별 활성화, 한 번 클릭.

REST API:
- `POST /generate` — `{"prompt": "...", "figure_kind": "auto|vector|raster|mixed"}` → `{session_id, artifact, kind, routing_reason}`
- `POST /edit/{session_id}` — `{"instruction": "...", "mask": "<base64 PNG>?"}` → `{session_id, artifact, kind, revision}`
- `GET /export/{session_id}/svg` — SVG 세션만
- `GET /export/{session_id}/pptx` — 양쪽 (raster는 L1 picture, vector는 L2 SVG-embedded)
- `GET /export/{session_id}/image` — raster 세션만
- `GET /health`

## 테스트

```bash
uv run pytest                                           # mocked 276개
uv run pytest --cov=app --cov-report=term-missing
uv run pytest --run-live                                # Gemini 비용 발생
```

## 아키텍처

```
┌──────────────────────────────────────────────────────────────────┐
│  FIGURE STUDIO (Gradio UI, /ui에 마운트)                           │
│  모드 · 모델 선택 · 실시간 미리보기 · candidate 네비 · export       │
└─────────────┬────────────────────────────────────────────────────┘
              │
┌─────────────▼────────────────────────────────────────────────────┐
│  FastAPI app                                                      │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  Orchestrator                                            │    │
│  │  router.decide() → A | B | C | D   (또는 명시적 override)  │    │
│  │  → tool로 dispatch  (progress + on_preview 콜백)           │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                   │
│  Tools:                                                           │
│   ├── vector_schematic   Path A: Gemini text + symbol library    │
│   ├── molecule           Path B: Gemini 추출 + RDKit             │
│   ├── raster_illustration Path C: Gemini Image (Nano Banana)     │
│   ├── mixed_schematic     Path D: 백본 + 생성 아이콘             │
│   │     ├── arrow_clip          connector → 아이콘 가장자리 클립  │
│   │     ├── label_declutter     라벨/connector 충돌 해소          │
│   │     └── layout_review        vision critic (keep-best ×3)     │
│   ├── inpaint            Path C 편집: mask 또는 자연어             │
│   ├── export            SVG / PPTX (L1) / image                  │
│   └── export_svg_pptx   PPTX (L2) — asvg:svgBlip로 SVG 임베드     │
│                                                                   │
│  Session store: 인메모리, TTL 만료                                  │
│  Gemini client: 비동기 wrapper (retry / structured output /       │
│                 요청별 모델 override 지원)                         │
└───────────────────────────────────────────────────────────────────┘
```

`docs/progress/INDEX.md` 에 단계별 개발 로그.

## 알려진 한계

- **Path C / 아이콘은 JPEG**: `gemini-3.1-flash-image-preview`가 JPEG 반환. MIME 자동 감지되어 data URI와 export에 반영.
- **Background removal 보류**: 스펙 #4. 출력이 이미 흰 배경. 후보: `rembg` (U2Net).
- **PowerPoint 2016 미만**: L2 PPTX (SVG 임베드) 는 1×1 placeholder PNG로 fallback; 모던 PowerPoint (2016+) 에서 SVG 렌더 + Convert to Shape.
- **결정론적 pass는 직선 `<line>` connector 대상**: bezier `<path>` 라우팅은 아직 clip/declutter 미지원.
- **극단적 종횡비 아이콘**: 여전히 목표 면적보다 작게 clamp됨; 아이콘 프레이밍을 상류(아이콘 스타일 prompt)에서 수렴시키는 게 향후 개선점.
- **영속성 없음**: 세션·candidate는 인메모리. 다운로드해야만 디스크에 저장 (브라우저 다운로드 폴더; 서버는 `$TMPDIR/figure_*`에 임시 생성).
- **Frontend는 Gradio**: 장기 계획은 Next.js + Konva (lasso, 라벨 드래그 등 풍부한 캔버스 편집).

## 비용

요청당 비용:
- Vector (Path D) 생성: pass당 ~$0.0001 text + 고유 아이콘당 image-gen (설명 기준 캐시); critic은 pass당 vision call 1회 추가.
- Path A / B 생성: ~$0.0001 (text) — 무시 가능.
- Illustration (Path C) 생성: ~$0.04 (image).
- Inpainting: ~$0.04 (image edit).
- Routing: 요청당 ~$0.0001 (명시적 Illustration/Vector는 생략).

## 라이선스

MIT — [LICENSE](LICENSE) 참조.
