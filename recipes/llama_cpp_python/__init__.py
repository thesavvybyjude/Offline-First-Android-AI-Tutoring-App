"""
python-for-android recipe for llama-cpp-python.

Cross-compiles llama.cpp with the Android NDK (CPU-only, ARM64 NEON)
and installs the Python ctypes bindings.

Build strategy:
  1. Download llama-cpp-python source (includes vendored llama.cpp)
  2. Use CMake + NDK toolchain to build libllama.so for arm64-v8a
  3. Install the Python package with the pre-built shared library

Tested with: llama-cpp-python 0.2.90, NDK r25b, API 28, arm64-v8a
"""

from os.path import join, exists
from pythonforandroid.recipe import Recipe
from pythonforandroid.toolchain import shprint, current_directory
from pythonforandroid.logger import info, warning
import sh
import os


class LlamaCppPythonRecipe(Recipe):
    version = "0.2.90"
    url = "https://github.com/abetlen/llama-cpp-python/archive/refs/tags/v{version}.tar.gz"
    name = "llama-cpp-python"
    depends = ["python3", "setuptools"]
    # Ensure the C++ shared STL is bundled in the APK
    need_stl_shared = True

    def get_recipe_env(self, arch):
        env = super().get_recipe_env(arch)

        ndk = self.ctx.ndk_dir
        toolchain_file = join(ndk, "build", "cmake", "android.toolchain.cmake")

        # C++ flags for ARM64 Android
        env["CXXFLAGS"] = env.get("CXXFLAGS", "") + " -std=c++17 -fPIC -O2"
        env["CFLAGS"] = env.get("CFLAGS", "") + " -fPIC -O2"
        env["LDFLAGS"] = env.get("LDFLAGS", "") + " -lc++_shared"

        # Tell scikit-build / CMake how to cross-compile
        cmake_args = " ".join([
            f"-DCMAKE_TOOLCHAIN_FILE={toolchain_file}",
            f"-DANDROID_ABI={arch.arch}",
            "-DANDROID_PLATFORM=android-28",
            "-DANDROID_STL=c++_shared",
            # --- llama.cpp build flags (CPU-only, no GPU) ---
            "-DLLAMA_NATIVE=OFF",
            "-DLLAMA_AVX=OFF",
            "-DLLAMA_AVX2=OFF",
            "-DLLAMA_AVX512=OFF",
            "-DLLAMA_FMA=OFF",
            "-DLLAMA_F16C=OFF",
            "-DLLAMA_METAL=OFF",
            "-DLLAMA_CUDA=OFF",
            "-DLLAMA_VULKAN=OFF",
            "-DLLAMA_OPENCL=OFF",
            "-DLLAMA_HIPBLAS=OFF",
            "-DLLAMA_STATIC=OFF",
            "-DBUILD_SHARED_LIBS=ON",
            "-DLLAMA_BUILD_TESTS=OFF",
            "-DLLAMA_BUILD_EXAMPLES=OFF",
            "-DLLAMA_BUILD_SERVER=OFF",
        ])
        env["CMAKE_ARGS"] = cmake_args
        env["FORCE_CMAKE"] = "1"

        return env

    def build_arch(self, arch):
        """
        Two-phase build:
          Phase 1: CMake builds libllama.so (the C/C++ inference core)
          Phase 2: Install the Python package into the target site-packages
        """
        source_dir = self.get_build_dir(arch.arch)
        env = self.get_recipe_env(arch)
        ndk = self.ctx.ndk_dir
        toolchain_file = join(ndk, "build", "cmake", "android.toolchain.cmake")

        # ---- Phase 1: Build libllama.so with CMake ----
        build_dir = join(source_dir, "_build_android")
        os.makedirs(build_dir, exist_ok=True)

        # The vendored llama.cpp source is inside vendor/llama.cpp
        # In llama-cpp-python 0.2.x, the C source is at vendor/llama.cpp
        vendor_dir = join(source_dir, "vendor", "llama.cpp")
        if not exists(vendor_dir):
            # Fallback: some versions bundle it differently
            vendor_dir = source_dir

        info(f"Building llama.cpp from {vendor_dir}")

        cmake = sh.Command("cmake")
        with current_directory(build_dir):
            shprint(cmake,
                    f"-DCMAKE_TOOLCHAIN_FILE={toolchain_file}",
                    f"-DANDROID_ABI={arch.arch}",
                    "-DANDROID_PLATFORM=android-28",
                    "-DANDROID_STL=c++_shared",
                    "-DCMAKE_BUILD_TYPE=Release",
                    "-DLLAMA_NATIVE=OFF",
                    "-DLLAMA_AVX=OFF",
                    "-DLLAMA_AVX2=OFF",
                    "-DLLAMA_AVX512=OFF",
                    "-DLLAMA_FMA=OFF",
                    "-DLLAMA_F16C=OFF",
                    "-DLLAMA_METAL=OFF",
                    "-DLLAMA_CUDA=OFF",
                    "-DLLAMA_VULKAN=OFF",
                    "-DLLAMA_OPENCL=OFF",
                    "-DLLAMA_HIPBLAS=OFF",
                    "-DBUILD_SHARED_LIBS=ON",
                    "-DLLAMA_BUILD_TESTS=OFF",
                    "-DLLAMA_BUILD_EXAMPLES=OFF",
                    "-DLLAMA_BUILD_SERVER=OFF",
                    vendor_dir,
                    _env=env)

            shprint(sh.make, "-j", str(os.cpu_count() or 4), _env=env)

        # Find the built libllama.so and copy it to the target libs directory
        lib_so = None
        for root, dirs, files in os.walk(build_dir):
            for f in files:
                if f.startswith("libllama") and f.endswith(".so"):
                    lib_so = join(root, f)
                    break
            if lib_so:
                break

        if lib_so:
            libs_dir = self.ctx.get_libs_dir(arch.arch)
            shprint(sh.cp, lib_so, libs_dir)
            info(f"Copied {lib_so} → {libs_dir}")

            # Also copy to where the Python ctypes loader expects it
            site_dir = self.ctx.get_python_install_dir(arch.arch)
            llama_cpp_dir = join(site_dir, "llama_cpp")
            os.makedirs(llama_cpp_dir, exist_ok=True)
            shprint(sh.cp, lib_so, llama_cpp_dir)
        else:
            warning("libllama.so not found after build!")

        # ---- Phase 2: Install Python package ----
        hostpython = sh.Command(self.hostpython_location)
        with current_directory(source_dir):
            # Install just the Python files (skip C build, we did it above)
            shprint(
                hostpython,
                "setup.py", "install",
                "--prefix", self.ctx.get_python_install_dir(arch.arch),
                "--install-lib", self.ctx.get_site_packages_dir(arch),
                _env=env,
            )

        info("llama-cpp-python recipe built successfully")


recipe = LlamaCppPythonRecipe()
