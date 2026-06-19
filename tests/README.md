# Test Suite — Offline-First AI Tutoring System

## Run all tests
```bash
pytest tests/ -v
```

## Run one phase
```bash
pytest tests/test_phase1_environment.py -v
pytest tests/test_phase2_rag_pipeline.py -v
pytest tests/test_phase3_sm2_scheduler.py -v
pytest tests/test_phase4_android_ui.py -v
pytest tests/test_phase5_sync_layer.py -v
pytest tests/test_phase6_integration_benchmarking.py -v
```

## Environment variables
| Variable | Default | Description |
|---|---|---|
| `TUTOR_MODEL_PATH` | `models/phi3-mini-q4_k_m.gguf` | GGUF model file path |
| `TUTOR_INDEX_PATH` | `data/corpus.index` | FAISS index file path |
| `TUTOR_CORPUS_DIR` | `data/corpus/` | Extracted text corpus directory |
| `TUTOR_GOLD_PATH` | `data/gold_qa_100.json` | Gold-standard Q&A evaluation set |
| `TUTOR_BENCHMARK_CSV` | `data/benchmark_results.csv` | Hardware benchmark results |
| `TUTOR_F1_RESULTS` | `data/f1_results.json` | RAG F1 evaluation output |
| `TUTOR_APK_PATH` | `bin/tutorapp-debug.apk` | Buildozer APK output |
| `TUTOR_SUS_PATH` | `data/uat_sus_scores.json` | UAT SUS scores file |

## Test files
| File | Phase | Groups | Tests |
|---|---|---|---|
| `conftest.py` | All | Fixtures | Shared DB, embeddings, chunks |
| `test_phase1_environment.py` | 1 | 5 | 29 |
| `test_phase2_rag_pipeline.py` | 2 | 5 | 29 |
| `test_phase3_sm2_scheduler.py` | 3 | 6 | 38 |
| `test_phase4_android_ui.py` | 4 | 6 | 32 |
| `test_phase5_sync_layer.py` | 5 | 5 | 29 |
| `test_phase6_integration_benchmarking.py` | 6 | 6 | 30 |
| **Total** | | **33** | **187** |

## Test strategy notes
- **Phase 1–3 tests** run entirely on CPU with no GPU, no internet, no real model.
- **Phase 4 tests** mock the RAG and LLM engines — no Kivy display required.
- **Phase 5 tests** use in-memory SQLite and a local Flask thread.
- **Phase 6 tests** skip gracefully (not fail) when data files don't exist yet.
- Tests tagged with `pytest.skip()` will auto-pass until the build artifact exists.
