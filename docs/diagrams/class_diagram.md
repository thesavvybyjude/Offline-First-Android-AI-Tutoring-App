# Class Diagram - AI Tutor App

## Core Classes

### Database Layer
```
DatabaseManager
--------------
- db_path: str
- conn: sqlite3.Connection
--------------
+ __init__(db_path: str)
+ connect(): Connection
+ close()
+ create_student(name, grade_level, school_id): int
+ get_student(student_id): Dict
+ create_knowledge_item(subject, question, answer, source_chunk, chunk_id): int
+ get_knowledge_item(item_id): Dict
+ create_repetition_record(student_id, item_id): int
+ get_repetition_record(student_id, item_id): Dict
+ update_repetition_record(student_id, item_id, quality): Dict
+ get_due_items(student_id, limit): List[Dict]
+ get_student_stats(student_id): Dict
+ get_unsynced_records(table_name): List[Dict]
+ mark_as_synced(table_name, record_id)
+ _log_sync_action(student_id, table_name, record_id, action)
```

### RAG Pipeline
```
RAGPipeline
--------------
- model_name: str
- index_path: str
- chunks_path: str
- embedding_model: SentenceTransformer
- index: faiss.Index
- chunks: List[Dict]
- embeddings: np.ndarray
--------------
+ __init__(model_name, index_path, chunks_path)
+ load_embedding_model()
+ encode_text(text: str): np.ndarray
+ encode_batch(texts: List[str]): np.ndarray
+ load_chunks(): List[Dict]
+ build_index(chunks: List[Dict])
+ save_index()
+ load_index()
+ search(query: str, top_k, threshold): List[Dict]
+ retrieve_context(query: str, max_tokens): str
```

### Inference Engine
```
InferenceEngine
--------------
- model_path: str
- n_ctx: int
- n_gpu_layers: int
- model: Llama
- prompt_template: str
--------------
+ __init__(model_path, n_ctx, n_gpu_layers)
+ load_model()
+ generate(query, context, grade_level, max_tokens, temperature, stream): str
+ _generate(prompt, max_tokens, temperature): str
+ _stream_generate(prompt, max_tokens, temperature): Generator
+ set_prompt_template(template: str)
+ generate_flashcard(chunk_text, subject): Dict
```

### SM2 Scheduler
```
SM2Scheduler
--------------
- db: DatabaseManager
--------------
+ __init__(db_manager)
+ calculate_next_review(quality, ease_factor, interval, repetitions): Dict
+ schedule_review(student_id, item_id, quality): Dict
+ get_due_items(student_id, limit): List[Dict]
+ get_review_session(student_id, session_size): Dict
+ seed_flashcards_from_chunks(chunks, inference_engine): int
+ get_learning_curve(student_id, days): List[Dict]
```

### Sync Layer
```
SyncLayer
--------------
- db: DatabaseManager
- server_url: str
- app: Flask
--------------
+ __init__(db_manager, server_url)
+ _setup_routes()
+ _process_server_change(change): Dict
+ _sync_student(data, action): Dict
+ _sync_repetition_record(data, action): Dict
+ push_changes(student_id): Dict
+ pull_changes(student_id): Dict
+ sync(student_id): Dict
+ run_server(host, port, debug)
```

### Corpus Processor
```
CorpusProcessor
--------------
- corpus_dir: str
- chunks_dir: str
--------------
+ __init__(corpus_dir, chunks_dir)
+ extract_text_from_pdf(pdf_path, method): str
+ _extract_with_pymupdf(pdf_path): str
+ _extract_with_pdfplumber(pdf_path): str
+ process_corpus_directory(pattern): List[Dict]
+ _infer_subject(filename): str
+ semantic_chunking(text, chunk_size, overlap, min_chunk_size): List[Dict]
+ _split_into_sentences(text): List[str]
+ _get_overlap_sentences(sentences, overlap_tokens): List[str]
+ chunk_document(document, chunk_size, overlap): List[Dict]
+ process_all_documents(chunk_size, overlap): List[Dict]
+ get_chunks(): List[Dict]
```

### UI Screens (Kivy)
```
LoginScreen (Screen)
--------------
- student_id_input: TextInput
- school_code_input: TextInput
- offline_checkbox: CheckBox
--------------
+ __init__(**kwargs)
+ _build_ui()
+ on_login(instance)

DashboardScreen (Screen)
--------------
- db: DatabaseManager
- student_id: int
- streak_label: Label
- due_label: Label
- retention_label: Label
- mastered_label: Label
--------------
+ __init__(**kwargs)
+ on_enter()
+ _build_ui()
+ _update_stats()
+ go_to_review(instance)
+ go_to_tutor(instance)
+ go_to_settings(instance)
+ logout(instance)

TutorChatScreen (Screen)
--------------
- rag: RAGPipeline
- inference: InferenceEngine
- chat_layout: BoxLayout
- message_input: TextInput
- messages: List
--------------
+ __init__(**kwargs)
+ on_enter()
+ _build_ui()
+ send_message(instance)
+ _add_message(text, is_user)
+ _get_ai_response(query)
+ go_back(instance)

ReviewScreen (Screen)
--------------
- db: DatabaseManager
- scheduler: SM2Scheduler
- student_id: int
- current_item: Dict
- items_queue: List
- is_flipped: bool
- card_layout: BoxLayout
- question_label: Label
- answer_label: Label
--------------
+ __init__(**kwargs)
+ on_enter()
+ _build_ui()
+ _load_due_items()
+ _show_next_card()
+ _update_progress()
+ flip_card(instance)
+ rate_card(rating)
+ go_back(instance)

SettingsScreen (Screen)
--------------
- db: DatabaseManager
- student_id: int
- name_input: TextInput
- subject_input: TextInput
- limit_slider: Slider
- sync_switch: Switch
--------------
+ __init__(**kwargs)
+ on_enter()
+ _build_ui()
+ _load_student_data()
+ _update_limit_label(instance, value)
+ _update_storage_usage()
+ clear_cache(instance)
+ save_settings(instance)
+ go_back(instance)
```

## Relationships

- **DatabaseManager** is used by: SM2Scheduler, SyncLayer, DashboardScreen, ReviewScreen, SettingsScreen
- **RAGPipeline** uses: SentenceTransformer, faiss
- **InferenceEngine** uses: Llama (llama-cpp-python)
- **SM2Scheduler** uses: DatabaseManager, InferenceEngine (for flashcard generation)
- **SyncLayer** uses: DatabaseManager, Flask
- **CorpusProcessor** is used by: RAGPipeline (for chunks)
- All **Screens** inherit from: Kivy Screen
- **TutorChatScreen** uses: RAGPipeline, InferenceEngine
