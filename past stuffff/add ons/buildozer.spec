[app]
# App title and package
title = AI Tutor
package.name = aitutor
package.domain = org.aitutor

# Entry point
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,gguf,index
source.include_patterns = models/*.gguf, data/**

version = 1.0.0

# Requirements — ordered by size (large first for cache efficiency)
# llama-cpp-python must be built with CPU-only flag for Android
requirements =
    python3,
    kivy==2.3.0,
    kivymd==1.1.1,
    sqlite3,
    numpy,
    faiss-cpu,
    sentence-transformers,
    llama-cpp-python,
    jinja2,
    flask

# Android settings
android.permissions =
    INTERNET,
    ACCESS_NETWORK_STATE,
    READ_EXTERNAL_STORAGE,
    WRITE_EXTERNAL_STORAGE

android.api = 33
android.minapi = 28
android.ndk = 25b
android.sdk = 33
android.arch = arm64-v8a

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

# Large file support (GGUF model is ~2.1GB)
android.gradle_dependencies =
    com.android.support:appcompat-v7:28.0.0

[buildozer]
log_level = 2
warn_on_root = 1

# Build output directory
bin_dir = ./bin

# NDK/SDK cache
android.ndk_path = ~/.buildozer/android/platform/android-ndk-r25b
android.sdk_path = ~/.buildozer/android/platform/android-sdk

# p4a (python-for-android) settings
p4a.branch = master

# Custom hook to disable GPU layers for llama-cpp on Android
# (CPU inference only — no OpenCL/Vulkan)
p4a.local_recipes = ./recipes
