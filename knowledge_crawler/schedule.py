"""Knowledge crawler schedule — APScheduler-based auto-update.

Runs weekly crawls of PubMed, WHO, CDC, and Vietnam MOH.
Summarizes findings, suggests rule updates, and writes to knowledge brain.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

DEFAULT_SCHEDULE = "0 2 * * 0"


class CrawlScheduler:
    def __init__(self, schedule: str | None = None) -> None:
        self.schedule = schedule or os.environ.get("KNOWLEDGE_CRAWL_SCHEDULE", DEFAULT_SCHEDULE)
        self._jobs: dict[str, object] = {}
        self._running = False

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.cron import CronTrigger

            self._scheduler = BackgroundScheduler()
            trigger = CronTrigger.from_crontab(self.schedule)
            self._scheduler.add_job(
                self._run_crawl_cycle,
                trigger=trigger,
                id="weekly_knowledge_crawl",
                name="PHTA Weekly Knowledge Crawl",
                replace_existing=True,
            )
            self._scheduler.start()
            logger.info(f"Knowledge crawler scheduled: {self.schedule}")
        except ImportError:
            logger.warning("APScheduler not installed — knowledge crawler will run on-demand only")
        except Exception:
            logger.exception("Failed to start knowledge crawler scheduler")

    def stop(self) -> None:
        if not self._running:
            return
        try:
            self._scheduler.shutdown(wait=False)
        except Exception:
            pass
        self._running = False

    def _run_crawl_cycle(self) -> None:
        import asyncio
        from knowledge_crawler.crawler import crawl_all
        from knowledge_crawler.clinical_summarizer import summarize_batch
        from knowledge_crawler.updater import suggest_rule_updates, update_knowledge_brain

        try:
            logger.info("Starting weekly knowledge crawl cycle")
            articles = asyncio.run(crawl_all())
            if articles:
                summaries = summarize_batch(articles)
                count = update_knowledge_brain(summaries, auto_approve=False)
                suggested = suggest_rule_updates(summaries)
                logger.info(f"Crawl complete: {len(articles)} articles, {count} entries added, {len(suggested)} rule suggestions")
            else:
                logger.info("Crawl complete: no new articles found")
        except Exception:
            logger.exception("Knowledge crawl cycle failed")

    def run_once(self) -> list[dict]:
        import asyncio
        from knowledge_crawler.crawler import crawl_all
        return asyncio.run(crawl_all())


def get_schedule_info() -> dict:
    return {
        "schedule": os.environ.get("KNOWLEDGE_CRAWL_SCHEDULE", DEFAULT_SCHEDULE),
        "description": "Weekly clinical knowledge crawl from PubMed, WHO, CDC, Vietnam MOH",
        "next_run": "Sunday at 02:00 local time",
    }
