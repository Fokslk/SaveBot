





from __future__ import annotations

import argparse
import sys
import time


def main() -> None:
    parser = argparse.ArgumentParser(description="Save Mod")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Запуск бота без GUI (один процесс, без панели)",
    )
    parser.add_argument(
        "--console",
        action="store_true",
        help="В headless-режиме рисовать ANSI-дашборд в консоли",
    )
    args = parser.parse_args()

    if not args.headless:
        from bot.panel import main as panel_main

        panel_main()
        return

    from bot.dashboard import prepare_console, start_dashboard, stop_dashboard
    from bot.instance import ensure_single_instance, kill_foreign_bots
    from bot.runtime_stats import STATS
    from bot.runner import BotRunner, setup_logging

    kill_foreign_bots()
    ensure_single_instance(kill_others=False)
    setup_logging(console=not args.console)
    prepare_console()

    runner = BotRunner()
    dash_stop = None
    if args.console:
        dash_stop, _ = start_dashboard(interval=1.0)

    runner.start()
    try:
        while runner.is_running:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        runner.stop()
        if dash_stop is not None:
            stop_dashboard(dash_stop)
        STATS.set_status("stopped")


if __name__ == "__main__":
    main()
