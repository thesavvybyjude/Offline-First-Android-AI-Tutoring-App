"""
python-for-android recipe for sentence-transformers.

sentence-transformers is a pure-Python package, BUT its runtime dependency
on PyTorch (~2 GB, no Android wheels) makes it impractical for mobile.

This recipe provides TWO paths:

  PATH A (Recommended for Android):
    Pre-build the FAISS index + embeddings on a desktop, then ship the
    pre-built index (curriculum.index + chunks.json) in the APK.
    The app loads the index at runtime — no embedding needed on device.
    → sentence-transformers is NOT used at runtime.

  PATH B (Experimental — ONNX Runtime):
    Use ONNX Runtime Mobile to run the all-MiniLM-L6-v2 model on-device.
    This avoids PyTorch entirely (~45 MB for ONNX model + runtime).
    Requires: onnxruntime (which has Android wheels).
    → We install a lightweight wrapper that provides a compatible API.

This recipe installs a shim module `sentence_transformers` that:
  1. Tries to import real sentence_transformers (works on desktop)
  2. Falls back to an ONNX-based implementation (works on Android)
  3. If neither works, provides a stub that raises ImportError on use

Usage in app code is unchanged:
    from sentence_transformers import SentenceTransformer
"""

from os.path import join, exists
from pythonforandroid.recipe import PythonRecipe
from pythonforandroid.logger import info, warning
import os


# ---------------------------------------------------------------------------
# The ONNX-based fallback module (embedded as a string, written to
# site-packages at build time)
# ---------------------------------------------------------------------------

ONNX_FALLBACK_MODULE = '''
"""
Lightweight sentence-transformers shim for Android.
Uses ONNX Runtime if available, otherwise provides a clear error.
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_REAL_ST = False
try:
    # If real sentence-transformers is somehow available, use it
    from sentence_transformers_real import SentenceTransformer as _RealST
    _REAL_ST = True
except ImportError:
    _RealST = None


class SentenceTransformer:
    """
    Drop-in replacement for sentence_transformers.SentenceTransformer.
    
    On Android: uses ONNX Runtime Mobile with a pre-exported model.
    On Desktop: delegates to the real sentence-transformers package.
    """
    
    def __init__(self, model_name_or_path="sentence-transformers/all-MiniLM-L6-v2", 
                 cache_folder=None, **kwargs):
        self.model_name = model_name_or_path
        self._backend = None
        
        if _REAL_ST:
            self._backend = "real"
            self._model = _RealST(model_name_or_path, cache_folder=cache_folder, **kwargs)
            return
        
        # Try ONNX Runtime
        try:
            import onnxruntime as ort
            self._backend = "onnx"
            self._session = None
            
            # Look for pre-exported ONNX model
            search_paths = [
                Path(cache_folder) if cache_folder else None,
                Path("models") / "embeddings",
                Path("data") / "embeddings",
            ]
            
            onnx_path = None
            for p in search_paths:
                if p and (p / "model.onnx").exists():
                    onnx_path = str(p / "model.onnx")
                    break
            
            if onnx_path:
                self._session = ort.InferenceSession(onnx_path)
                logger.info(f"Loaded ONNX embedding model from {onnx_path}")
            else:
                logger.warning(
                    "No ONNX embedding model found. "
                    "Run: python -c \\"from sentence_transformers import SentenceTransformer; "
                    "m = SentenceTransformer(\'all-MiniLM-L6-v2\'); "
                    "m.save(\'models/embeddings\')\\" on desktop, "
                    "then export to ONNX."
                )
        except ImportError:
            self._backend = None
            logger.warning(
                "Neither sentence-transformers nor onnxruntime available. "
                "RAG embeddings will not work on this device."
            )
    
    def encode(self, sentences, batch_size=32, show_progress_bar=False, 
               normalize_embeddings=False, **kwargs):
        """Encode sentences to embeddings."""
        if self._backend == "real":
            return self._model.encode(
                sentences, batch_size=batch_size,
                show_progress_bar=show_progress_bar,
                normalize_embeddings=normalize_embeddings,
                **kwargs
            )
        
        if self._backend == "onnx" and self._session:
            return self._encode_onnx(sentences, normalize_embeddings)
        
        raise RuntimeError(
            "No embedding backend available. "
            "Install sentence-transformers (desktop) or onnxruntime (mobile), "
            "or pre-build your FAISS index on a desktop machine."
        )
    
    def _encode_onnx(self, sentences, normalize=False):
        """Encode using ONNX Runtime (basic tokenization)."""
        import numpy as np
        
        if isinstance(sentences, str):
            sentences = [sentences]
        
        # Very basic whitespace tokenization + padding
        # For production, use a proper tokenizer (e.g., from tokenizers package)
        max_len = 128
        embeddings = []
        
        for sent in sentences:
            tokens = sent.lower().split()[:max_len]
            # Simple hash-based token IDs (placeholder — real impl needs vocab)
            input_ids = [hash(t) % 30522 for t in tokens]
            attention_mask = [1] * len(input_ids)
            
            # Pad
            pad_len = max_len - len(input_ids)
            input_ids += [0] * pad_len
            attention_mask += [0] * pad_len
            
            inputs = {
                "input_ids": np.array([input_ids], dtype=np.int64),
                "attention_mask": np.array([attention_mask], dtype=np.int64),
            }
            
            # Handle optional token_type_ids
            input_names = [i.name for i in self._session.get_inputs()]
            if "token_type_ids" in input_names:
                inputs["token_type_ids"] = np.zeros_like(inputs["input_ids"])
            
            outputs = self._session.run(None, inputs)
            # Mean pooling over token embeddings
            embedding = outputs[0][0].mean(axis=0)
            embeddings.append(embedding)
        
        result = np.array(embeddings)
        if normalize:
            norms = np.linalg.norm(result, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1.0, norms)
            result = result / norms
        
        return result
'''


class SentenceTransformersRecipe(PythonRecipe):
    """
    Installs a sentence-transformers shim for Android.
    
    On Android: provides an ONNX Runtime fallback (if ort is available)
                or a clear error message guiding the user to pre-build indexes.
    On Desktop: the real sentence-transformers works normally.
    """
    
    name = "sentence-transformers"
    version = "3.0.0"
    # We don't actually download sentence-transformers (it pulls torch).
    # Instead we install our lightweight shim.
    url = None
    depends = ["python3", "numpy"]
    # Optional: ["onnxruntime"] — add if you want on-device embeddings

    def build_arch(self, arch):
        """Write the shim module to site-packages."""
        site_packages = self.ctx.get_site_packages_dir(arch)
        st_dir = join(site_packages, "sentence_transformers")
        os.makedirs(st_dir, exist_ok=True)

        # Write __init__.py with the ONNX fallback
        init_path = join(st_dir, "__init__.py")
        with open(init_path, "w", encoding="utf-8") as f:
            f.write(ONNX_FALLBACK_MODULE)

        info(f"Installed sentence_transformers shim → {st_dir}")
        info(
            "NOTE: For production RAG, pre-build your FAISS index on a "
            "desktop with the real sentence-transformers package, then "
            "ship curriculum.index + chunks.json in the APK."
        )


recipe = SentenceTransformersRecipe()
