from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional


class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"

    BG_GREEN = "\033[42m"
    BG_RED = "\033[41m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"


@dataclass
class PrettyLogger:
    name: str
    enable_color: bool = True

    def __post_init__(self) -> None:
        self._start_time = time.time()

    def _c(self, color: str, text: str) -> str:
        if self.enable_color:
            return f"{color}{text}{Colors.RESET}"
        return text

    def _timestamp(self) -> str:
        elapsed = time.time() - self._start_time
        return f"[{elapsed:6.2f}s]"

    def header(self, text: str, width: int = 70) -> None:
        line = "=" * width
        print(f"\n{self._c(Colors.CYAN, line)}")
        print(self._c(Colors.BOLD + Colors.CYAN, f"  {text}"))
        print(f"{self._c(Colors.CYAN, line)}")

    def section(self, text: str) -> None:
        print(f"\n{self._c(Colors.YELLOW, '▶')} {self._c(Colors.BOLD, text)}")
        print(self._c(Colors.DIM, "─" * 50))

    def info(self, message: str) -> None:
        print(f"{self._c(Colors.DIM, self._timestamp())} {self._c(Colors.BLUE, 'ℹ')} {message}")

    def success(self, message: str) -> None:
        print(f"{self._c(Colors.DIM, self._timestamp())} {self._c(Colors.GREEN, '✓')} {message}")

    def warning(self, message: str) -> None:
        print(f"{self._c(Colors.DIM, self._timestamp())} {self._c(Colors.YELLOW, '⚠')} {message}")

    def error(self, message: str) -> None:
        print(f"{self._c(Colors.DIM, self._timestamp())} {self._c(Colors.RED, '✗')} {message}")

    def stage(self, stage_num: int, stage_name: str, status: str = "START") -> None:
        if status == "START":
            icon = self._c(Colors.MAGENTA, "●")
            label = self._c(Colors.BOLD + Colors.MAGENTA, f"Stage {stage_num}: {stage_name}")
        elif status == "DONE":
            icon = self._c(Colors.GREEN, "●")
            label = self._c(Colors.GREEN, f"Stage {stage_num}: {stage_name} - Complete")
        elif status == "SKIP":
            icon = self._c(Colors.DIM, "○")
            label = self._c(Colors.DIM, f"Stage {stage_num}: {stage_name} - Skipped")
        elif status == "BLOCK":
            icon = self._c(Colors.RED, "●")
            label = self._c(Colors.RED, f"Stage {stage_num}: {stage_name} - Blocked")
        else:
            icon = "○"
            label = f"Stage {stage_num}: {stage_name}"
        print(f"{self._c(Colors.DIM, self._timestamp())} {icon} {label}")

    def kv(self, key: str, value: Any, indent: int = 2) -> None:
        spaces = " " * indent
        key_str = self._c(Colors.CYAN, f"{key}:")
        print(f"{spaces}{key_str} {value}")

    def json_block(self, data: Dict, title: str = "", max_lines: int = 15) -> None:
        if title:
            print(f"  {self._c(Colors.DIM, title)}")
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        lines = json_str.split("\n")
        if len(lines) > max_lines:
            half = max_lines // 2
            display_lines = (
                lines[:half]
                + [self._c(Colors.DIM, f"    ... ({len(lines) - max_lines} lines omitted) ...")]
                + lines[-half:]
            )
        else:
            display_lines = lines
        for line in display_lines:
            print(f"  {self._c(Colors.DIM, '│')} {line}")

    def score_bar(self, label: str, score: int, max_score: int, width: int = 20) -> None:
        ratio = score / max_score if max_score > 0 else 0
        filled = int(width * ratio)
        empty = width - filled
        if ratio >= 0.8:
            bar_color = Colors.GREEN
        elif ratio >= 0.5:
            bar_color = Colors.YELLOW
        else:
            bar_color = Colors.RED
        bar = self._c(bar_color, "█" * filled) + self._c(Colors.DIM, "░" * empty)
        print(f"  {label:15} {bar} {score:3}/{max_score}")

    def divider(self, char: str = "─", width: int = 50) -> None:
        print(self._c(Colors.DIM, char * width))


_LOGGER: PrettyLogger = PrettyLogger("AutoDriveBenchmark", enable_color=True)


def get_logger() -> PrettyLogger:
    return _LOGGER


def set_logger(enable_color: bool = True, name: str = "AutoDriveBenchmark") -> PrettyLogger:
    global _LOGGER
    _LOGGER = PrettyLogger(name=name, enable_color=enable_color)
    return _LOGGER
