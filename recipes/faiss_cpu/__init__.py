"""
python-for-android recipe for faiss-cpu.

Cross-compiles Facebook AI Similarity Search (FAISS) for Android ARM64.
Uses OpenBLAS (built from source) for linear algebra and SWIG for Python bindings.

Build strategy:
  1. Build OpenBLAS for ARM64 (lightweight BLAS/LAPACK)
  2. Build FAISS with CMake + NDK (CPU-only, generic SIMD, GPU disabled)
  3. Build Python bindings via SWIG
  4. Install into target site-packages

Tested with: faiss-cpu 1.8.0, NDK r25b, API 28, arm64-v8a

IMPORTANT: This recipe requires `swig` to be installed on the build host:
    sudo apt install swig
"""

from os.path import join, exists
from pythonforandroid.recipe import Recipe
from pythonforandroid.toolchain import shprint, current_directory
from pythonforandroid.logger import info, warning
import sh
import os


class OpenBLASRecipe(Recipe):
    """
    Minimal OpenBLAS build for FAISS on Android ARM64.
    Built as part of the faiss_cpu recipe (not standalone).
    """
    version = "0.3.27"
    url = "https://github.com/OpenMathLib/OpenBLAS/archive/refs/tags/v{version}.tar.gz"
    name = "openblas"

    def build_for_android(self, arch, env, install_prefix):
        """Build OpenBLAS with the Android NDK. Returns install prefix."""
        source_dir = self.get_build_dir(arch.arch)
        ndk = self.ctx.ndk_dir
        toolchain = join(ndk, "build", "cmake", "android.toolchain.cmake")

        build_dir = join(source_dir, "_build")
        os.makedirs(build_dir, exist_ok=True)

        cmake = sh.Command("cmake")
        with current_directory(build_dir):
            shprint(cmake,
                    f"-DCMAKE_TOOLCHAIN_FILE={toolchain}",
                    f"-DANDROID_ABI={arch.arch}",
                    "-DANDROID_PLATFORM=android-28",
                    "-DCMAKE_BUILD_TYPE=Release",
                    f"-DCMAKE_INSTALL_PREFIX={install_prefix}",
                    # Minimal OpenBLAS config for FAISS
                    "-DNOFORTRAN=ON",
                    "-DNO_LAPACKE=ON",
                    "-DBUILD_WITHOUT_LAPACK=OFF",
                    "-DTARGET=ARMV8",
                    "-DBUILD_SHARED_LIBS=ON",
                    source_dir,
                    _env=env)
            shprint(sh.make, "-j", str(os.cpu_count() or 4), _env=env)
            shprint(sh.make, "install", _env=env)

        info(f"OpenBLAS built and installed to {install_prefix}")
        return install_prefix


class FaissCpuRecipe(Recipe):
    version = "1.8.0"
    url = "https://github.com/facebookresearch/faiss/archive/refs/tags/v{version}.tar.gz"
    name = "faiss-cpu"
    depends = ["python3", "setuptools", "numpy"]
    need_stl_shared = True

    def get_recipe_env(self, arch):
        env = super().get_recipe_env(arch)
        env["CXXFLAGS"] = env.get("CXXFLAGS", "") + " -std=c++17 -fPIC -O2"
        env["CFLAGS"] = env.get("CFLAGS", "") + " -fPIC -O2"
        env["LDFLAGS"] = env.get("LDFLAGS", "") + " -lc++_shared"
        return env

    def build_arch(self, arch):
        """
        Build FAISS for Android:
          1. Build OpenBLAS (or use pre-built)
          2. Configure FAISS with CMake
          3. Build C++ library
          4. Build Python bindings (SWIG)
        """
        source_dir = self.get_build_dir(arch.arch)
        env = self.get_recipe_env(arch)
        ndk = self.ctx.ndk_dir
        toolchain = join(ndk, "build", "cmake", "android.toolchain.cmake")

        # ---- Step 1: Build OpenBLAS for ARM64 ----
        openblas_prefix = join(source_dir, "_openblas_install")
        os.makedirs(openblas_prefix, exist_ok=True)

        openblas = OpenBLASRecipe()
        openblas.ctx = self.ctx
        openblas.recipe_dir = self.recipe_dir
        try:
            openblas.build_for_android(arch, env, openblas_prefix)
            has_blas = True
        except Exception as e:
            warning(f"OpenBLAS build failed: {e}. Building FAISS without optimized BLAS.")
            has_blas = False

        # ---- Step 2: Build FAISS C++ library ----
        build_dir = join(source_dir, "_build")
        os.makedirs(build_dir, exist_ok=True)

        cmake = sh.Command("cmake")
        cmake_args = [
            f"-DCMAKE_TOOLCHAIN_FILE={toolchain}",
            f"-DANDROID_ABI={arch.arch}",
            "-DANDROID_PLATFORM=android-28",
            "-DANDROID_STL=c++_shared",
            "-DCMAKE_BUILD_TYPE=Release",
            # FAISS config
            "-DFAISS_ENABLE_GPU=OFF",
            "-DFAISS_ENABLE_PYTHON=ON",
            "-DFAISS_OPT_LEVEL=generic",     # No AVX/SSE — use generic ARM code
            "-DBUILD_SHARED_LIBS=ON",
            "-DBUILD_TESTING=OFF",
        ]

        if has_blas:
            cmake_args.extend([
                f"-DCMAKE_PREFIX_PATH={openblas_prefix}",
                "-DBLA_VENDOR=OpenBLAS",
            ])

        # numpy headers for the Python bindings
        numpy_recipe = self.get_recipe("numpy", self.ctx)
        numpy_include = join(
            numpy_recipe.get_build_dir(arch.arch),
            "numpy", "core", "include"
        )
        if exists(numpy_include):
            cmake_args.append(f"-DPython_NumPy_INCLUDE_DIR={numpy_include}")

        with current_directory(build_dir):
            shprint(cmake, *cmake_args, source_dir, _env=env)
            shprint(sh.make, "-j", str(os.cpu_count() or 4), _env=env)

        # ---- Step 3: Copy built libraries ----
        libs_dir = self.ctx.get_libs_dir(arch.arch)
        for root, dirs, files in os.walk(build_dir):
            for f in files:
                if f.endswith(".so"):
                    src = join(root, f)
                    shprint(sh.cp, src, libs_dir)
                    info(f"Copied {f} → {libs_dir}")

        # ---- Step 4: Install Python package ----
        # FAISS Python bindings live in faiss/python/
        python_dir = join(source_dir, "faiss", "python")
        if exists(python_dir):
            site_packages = self.ctx.get_site_packages_dir(arch)
            faiss_target = join(site_packages, "faiss")
            os.makedirs(faiss_target, exist_ok=True)

            # Copy Python files
            for f in os.listdir(python_dir):
                src = join(python_dir, f)
                if f.endswith(".py"):
                    shprint(sh.cp, src, faiss_target)

            # Copy SWIG-generated wrapper
            swig_dir = join(build_dir, "faiss", "python")
            if exists(swig_dir):
                for f in os.listdir(swig_dir):
                    src = join(swig_dir, f)
                    if f.endswith(".py") or f.endswith(".so"):
                        shprint(sh.cp, src, faiss_target)

        info("faiss-cpu recipe built successfully")


recipe = FaissCpuRecipe()
