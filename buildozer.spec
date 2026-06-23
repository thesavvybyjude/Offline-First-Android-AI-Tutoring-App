[app]
# App title and package
title = ZIDON AI
package.name = aitutor
package.domain = org.aitutor

# Entry point
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,gguf,index,ttf,otf
source.include_patterns = models/*.gguf, data/**, assets/fonts/*.ttf
source.exclude_dirs = tests, files, add ons, docs, .github, .venv, bin, .git, recipes

version = 1.0.0

# Requirements — full AI build with on-device inference
# numpy 1.24.4: known to build with p4a (2.x has C++ STL issues)
# llama-cpp-python: on-device LLM inference (custom recipe in ./recipes)
# faiss-cpu: vector similarity search for RAG (custom recipe)
# sentence-transformers: embedding model shim (custom recipe, ONNX fallback)
requirements =
    hostpython3==3.11.8,
    python3==3.11.8,
    kivy==2.3.1,
    sqlite3,
    numpy==1.26.3,
    jinja2,
    markupsafe==2.1.2,
    llama-cpp-python==0.2.90,
    faiss-cpu==1.8.0,
    sentence-transformers==3.0.0

# Android settings
android.permissions =
    INTERNET,
    ACCESS_NETWORK_STATE

android.api = 33
android.minapi = 28
android.ndk = 25b
android.sdk = 33

# ABI — arm64-v8a only (covers 95%+ of Android devices since 2016)
android.archs = arm64-v8a

# Orientation
orientation = portrait

# Icons
icon.filename = %(source.dir)s/assets/icon.png
presplash.filename = %(source.dir)s/assets/splash.png

# Fullscreen
fullscreen = 0

# Build mode
android.release_artifact = apk

[buildozer]
log_level = 2
warn_on_root = 1

# Build output directory
bin_dir = ./bin

# NDK/SDK cache
android.ndk_path = ~/.buildozer/android/platform/android-ndk-r25b
android.sdk_path = ~/.buildozer/android/platform/android-sdk

# Custom p4a recipes for AI dependencies
# llama-cpp-python: CMake cross-compile for ARM64 CPU-only
# faiss-cpu: CMake + OpenBLAS for ARM64
# sentence-transformers: ONNX Runtime shim (avoids PyTorch)
p4a.local_recipes = ./recipes

# Use latest p4a for best NDK compatibility
p4a.branch = develop
