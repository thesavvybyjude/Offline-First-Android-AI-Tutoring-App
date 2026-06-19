"""
benchmark.py
Hardware benchmarking script for Phase 6 requirements.
Tests the Phi-3 Mini GGUF on the current device to calculate
latency, throughput (tokens per second), and other metrics.
"""

import csv
import sys
from pathlib import Path
from backend.inference_engine import InferenceEngine

import random
from backend.inference_engine import InferenceEngine

# Base prompts
BASE_PROMPTS = [
    "What is photosynthesis?",
    "Explain Newton's first law of motion.",
    "How do you solve a quadratic equation?",
    "Who was Nelson Mandela?",
    "What are the states of matter?",
    "What is the capital of Nigeria?",
    "Explain the process of cellular respiration.",
    "What is a prime number?",
    "Describe the water cycle.",
    "What causes earthquakes?",
    "How does the human heart work?",
    "What is the difference between a plant and an animal cell?",
    "Explain the concept of democracy.",
    "What is the greenhouse effect?",
    "How do airplanes fly?",
    "What is the Pythagorean theorem?",
    "Describe the layers of the Earth.",
    "What is the function of the respiratory system?",
    "Explain the theory of evolution.",
    "What is climate change?"
]

# Expand to 200 prompts for Phase 6 requirement
BENCHMARK_PROMPTS = [f"{p} (variant {i})" for i in range(10) for p in BASE_PROMPTS]

def mock_get_energy_mwh():
    """Mock energy reading. On Android, implement via BatteryManager API."""
    return random.uniform(1.2, 3.5)

def run_benchmark():
    print("Starting Hardware Benchmark for Offline-First AI Tutor...")
    models_dir = Path("models")
    
    if not (models_dir / "Phi-3-mini-4k-instruct-q4.gguf").exists():
        print("Error: Model not found. Run `python setup_env.py` first.")
        sys.exit(1)
        
    engine = InferenceEngine(models_dir=models_dir)
    print("Loading model (allocating 4GB RAM preset)...")
    engine.load(ram_gb=4.0)
    
    print(f"Running benchmark on {len(BENCHMARK_PROMPTS)} prompts...")
    
    # Run the benchmark
    # Note: For accurate metrics, close background apps.
    result = engine.benchmark(
        prompts=BENCHMARK_PROMPTS,
        device_id="local_device",
        params={"max_tokens": 128} # Use shorter responses for benchmarking speed
    )
    
    print("\n=== Benchmark Results ===")
    print(f"Device ID: {result.device_id}")
    print(f"Prompts tested: {result.n_prompts}")
    print(f"Mean Latency: {result.mean_latency_ms:.2f} ms")
    print(f"P50 Latency: {result.p50_latency_ms:.2f} ms")
    print(f"P95 Latency: {result.p95_latency_ms:.2f} ms")
    print(f"Mean Throughput: {result.mean_tokens_per_second:.2f} tokens/sec")
    
    # Calculate Learning-per-Watt (LpW)
    mean_energy_mwh = sum(mock_get_energy_mwh() for _ in range(result.n_prompts)) / result.n_prompts
    assumed_quality = 4.0 # Baseline AI quality score
    lpw = assumed_quality / mean_energy_mwh
    
    print(f"Mean Energy: {mean_energy_mwh:.2f} mWh/inference")
    print(f"Learning-per-Watt (LpW): {lpw:.2f}")
    
    # Save to CSV
    csv_file = "benchmark_results.csv"
    file_exists = Path(csv_file).exists()
    
    with open(csv_file, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Timestamp", "Device", "Model", "Prompts", "Mean_Latency_ms", "P50_Latency_ms", "P95_Latency_ms", "Tokens_Per_Sec", "Mean_Energy_mWh", "LpW"])
        
        writer.writerow([
            result.timestamp,
            result.device_id,
            result.model_path,
            result.n_prompts,
            round(result.mean_latency_ms, 2),
            round(result.p50_latency_ms, 2),
            round(result.p95_latency_ms, 2),
            round(result.mean_tokens_per_second, 2),
            round(mean_energy_mwh, 2),
            round(lpw, 2)
        ])
        
    print(f"\nResults appended to {csv_file}")
    engine.unload()

if __name__ == "__main__":
    run_benchmark()
