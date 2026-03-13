import os
import time
from datetime import datetime
from collections import defaultdict

class EngineProfiler:
    def __init__(self):
        self.enabled = True
        self.verbose = False

        os.makedirs(".logs", exist_ok=True)

        # Loop profiling
        self.loops = []

        # Opcode profiling
        self.opcode_counts = defaultdict(int)
        self.opcode_time_ns = defaultdict(int)

        # Expression profiling
        self.checkifvar_time_ns = 0
        self.checkifvar_calls = 0

        # Substack profiling
        self.substack_time_ns = 0
        self.substack_calls = 0

        self._loop_stack = []

    # -----------------------------
    # Loop profiling
    # -----------------------------

    def start_loop(self, name):
        if not self.enabled: return
        self._loop_stack.append({
            "name": name,
            "start": time.perf_counter_ns(),
            "iterations": 0
        })

    def tick_loop(self):
        if not self.enabled or not self._loop_stack: return
        self._loop_stack[-1]["iterations"] += 1

    def end_loop(self):
        if not self.enabled or not self._loop_stack: return
        data = self._loop_stack.pop()
        duration = time.perf_counter_ns() - data["start"]

        self.loops.append({
            "name": data["name"],
            "iterations": data["iterations"],
            "duration_ns": duration
        })

    # -----------------------------
    # Opcode profiling
    # -----------------------------

    def start_opcode(self, name):
        if not self.enabled: return None
        return time.perf_counter_ns()

    def end_opcode(self, name, start_time):
        if not self.enabled or start_time is None: return
        elapsed = time.perf_counter_ns() - start_time
        self.opcode_counts[name] += 1
        self.opcode_time_ns[name] += elapsed

    # -----------------------------
    # checkifvar profiling
    # -----------------------------

    def start_checkifvar(self):
        if not self.enabled:
            return None
        return time.perf_counter_ns()

    def end_checkifvar(self, start_time):
        try:
            if not self.enabled or start_time is None:
                return
            elapsed = time.perf_counter_ns() - start_time
            self.checkifvar_calls += 1
            self.checkifvar_time_ns += elapsed
        except:
            pass

    # -----------------------------
    # Substack profiling
    # -----------------------------

    def start_substack(self):
        if not self.enabled: return None
        return time.perf_counter_ns()

    def end_substack(self, start_time):
        if not self.enabled or start_time is None: return
        elapsed = time.perf_counter_ns() - start_time
        self.substack_calls += 1
        self.substack_time_ns += elapsed

    # -----------------------------
    # Export report
    # -----------------------------

    def export(self):
        if not self.enabled:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f".logs/run_{timestamp}.txt"

        with open(path, "w") as f:
            f.write("=== FLOPPY ENGINE FULL PROFILING REPORT ===\n")
            f.write(f"Generated: {timestamp}\n\n")

            # --------------------------------
            # Loop Report
            # --------------------------------
            f.write("=== LOOP PROFILING ===\n")
            for loop in self.loops:
                dur_us = loop["duration_ns"] / 1000
                avg_us = dur_us / max(1, loop["iterations"])
                ips = loop["iterations"] / (loop["duration_ns"] / 1e9)

                f.write(f"Loop: {loop['name']}\n")
                f.write(f"Iterations: {loop['iterations']}\n")
                f.write(f"Total: {dur_us:.3f} µs\n")
                f.write(f"Avg/Iter: {avg_us:.6f} µs\n")
                f.write(f"Iter/sec: {ips:,.2f}\n")
                f.write("-" * 50 + "\n")

            # --------------------------------
            # Opcode Report
            # --------------------------------
            f.write("\n=== OPCODE PROFILING ===\n")

            sorted_ops = sorted(
                self.opcode_time_ns.items(),
                key=lambda x: x[1],
                reverse=True
            )

            for name, total_ns in sorted_ops:
                count = self.opcode_counts[name]
                avg_ns = total_ns / max(1, count)

                f.write(f"{name}\n")
                f.write(f"  Calls: {count}\n")
                f.write(f"  Total: {total_ns / 1000:.3f} µs\n")
                f.write(f"  Avg: {avg_ns:.2f} ns\n")
                f.write("-" * 40 + "\n")

            # --------------------------------
            # Expression Stats
            # --------------------------------
            f.write("\n=== checkifvar PROFILING ===\n")
            f.write(f"Calls: {self.checkifvar_calls}\n")
            f.write(f"Total: {self.checkifvar_time_ns / 1000:.3f} µs\n")

            # --------------------------------
            # Substack Stats
            # --------------------------------
            f.write("\n=== SUBSTACK PROFILING ===\n")
            f.write(f"Calls: {self.substack_calls}\n")
            f.write(f"Total: {self.substack_time_ns / 1000:.3f} µs\n")

        print(f"[Profiler] Full log saved to {path}")