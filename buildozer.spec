[app]
# App title and package
title = AI Tutor
package.name = aitutor
package.domain = org.aitutor

# Entry point
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,gguf,index
source.include_patterns = models/*.gguf, data/**
source.exclude_dirs = tests, files, add ons, docs, .github, .venv, bin, .git

version = 1.0.0

# Requirements — UI-only mobile build (AI deps need custom p4a recipes)
# numpy, faiss-cpu, sentence-transformers, llama-cpp-python are NOT included here;
# they require custom p4a recipes for Android cross-compilation.
# Add them back when recipes/ is created.
requirements =
    hostpython3==3.11.8,
    python3==3.11.8,
    kivy==2.3.1,
    sqlite3,
    jinja2,
    markupsafe==2.1.2

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

# Note: llama-cpp-python, faiss-cpu, sentence-transformers require custom p4a recipes.
# This APK ships UI + flashcards; place a GGUF in models/ before build for on-device chat.
# Run: python setup_env.py  (downloads SmolLM2-360M ~270MB)
