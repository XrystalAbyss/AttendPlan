import time
import subprocess
from pathlib import Path

def run_benchmark():
    exe_path = Path("dist/AttendPlan/AttendPlan.exe").resolve()
    assert exe_path.exists(), f"Binary not found: {exe_path}"

    print(f"Benchmarking packaged binary: {exe_path}")
    version_times = []
    for i in range(3):
        t0 = time.perf_counter()
        p = subprocess.run([str(exe_path), "--version"], capture_output=True, text=True)
        dt = (time.perf_counter() - t0) * 1000
        version_times.append(dt)
        print(f"Run {i+1} (--version): {dt:.1f}ms (code={p.returncode}, out={p.stdout.strip()})")

    status_times = []
    for i in range(3):
        t0 = time.perf_counter()
        p = subprocess.run([str(exe_path), "--status"], capture_output=True, text=True)
        dt = (time.perf_counter() - t0) * 1000
        status_times.append(dt)
        print(f"Run {i+1} (--status): {dt:.1f}ms (code={p.returncode})")

    avg_version = sum(version_times) / len(version_times)
    avg_status = sum(status_times) / len(status_times)
    print(f"Average --version latency: {avg_version:.1f}ms")
    print(f"Average --status latency: {avg_status:.1f}ms")

if __name__ == "__main__":
    run_benchmark()

