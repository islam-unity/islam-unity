import sys
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("app.terminal_progress")


class TerminalProgress:
    """
    Renders clean, informative workflow stages, batch progress, and remaining percentage
    to the terminal (stdout) and backend loggers during data ingestion & AI processing.
    """

    BAR_WIDTH = 25
    LINE_WIDTH = 78

    @classmethod
    def _safe_print(cls, text: str):
        try:
            print(text, flush=True)
        except Exception:
            try:
                sys.stdout.buffer.write((text + "\n").encode("utf-8", errors="replace"))
                sys.stdout.flush()
            except Exception:
                pass

    @classmethod
    def print_stage(
        cls,
        stage_num: int,
        total_stages: int,
        title: str,
        details: Optional[str] = None
    ):
        """
        Announces a major workflow stage (مرحله / گام).
        """
        line = "═" * cls.LINE_WIDTH
        header = f" [گام {stage_num}/{total_stages}] {title} "
        msg = f"\n{line}\n{header}\n"
        if details:
            msg += f" {details}\n"
        msg += f"{line}\n"

        cls._safe_print(msg)
        logger.info(f"[Stage {stage_num}/{total_stages}] {title} - {details or ''}")

    @classmethod
    def print_batch_progress(
        cls,
        stage_num: int,
        total_stages: int,
        current_batch: int,
        total_batches: int,
        processed_items: int,
        total_items: int,
        batch_items_count: int,
        batch_details: str = ""
    ):
        """
        Renders live batch progress, completed percentage, and REMAINING percentage (درصد باقی‌مانده).
        """
        if total_items > 0:
            completed_pct = round((processed_items / total_items) * 100.0, 1)
        else:
            completed_pct = 100.0

        completed_pct = max(0.0, min(100.0, completed_pct))
        remaining_pct = round(100.0 - completed_pct, 1)
        remaining_items = max(0, total_items - processed_items)

        filled_len = int(cls.BAR_WIDTH * (completed_pct / 100.0))
        bar = "█" * filled_len + "░" * (cls.BAR_WIDTH - filled_len)

        divider = "─" * cls.LINE_WIDTH
        output_lines = [
            divider,
            f" [گام {stage_num}/{total_stages}] 🧠 پردازش دسته‌ای هوش مصنوعی | دسته {current_batch} از {total_batches} ({batch_items_count} چانک)",
            f"   پیشرفت:       [{bar}] {completed_pct:5.1f}% تکمیل شده",
            f"   ⏳ باقی‌مانده:  {remaining_pct:5.1f}% باقی‌مانده ({remaining_items} از {total_items} چانک در انتظار)",
        ]
        if batch_details:
            output_lines.append(f"   وضعیت دسته:   {batch_details}")
        output_lines.append(divider)

        cls._safe_print("\n".join(output_lines))
        logger.info(
            f"[Batch {current_batch}/{total_batches}] {completed_pct}% completed | "
            f"{remaining_pct}% remaining ({remaining_items}/{total_items} chunks left) - {batch_details}"
        )

    @classmethod
    def print_summary(
        cls,
        stage_num: int,
        total_stages: int,
        title: str,
        stats: Dict[str, Any]
    ):
        """
        Displays final completion summary with 100% completion and 0% remaining.
        """
        line = "═" * cls.LINE_WIDTH
        output_lines = [
            f"\n{line}",
            f" [گام {stage_num}/{total_stages}] ✅ {title}",
            f"   پیشرفت نهایی: [█████████████████████████] 100.0% تکمیل شد (0.0% باقی‌مانده)",
        ]
        for k, v in stats.items():
            output_lines.append(f"   • {k}: {v}")
        output_lines.append(f"{line}\n")

        cls._safe_print("\n".join(output_lines))
        logger.info(f"[Completed] {title} - {stats}")
