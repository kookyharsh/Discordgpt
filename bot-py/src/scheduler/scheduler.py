import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger("discord_agent_scheduler")

class AgentScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()

    def start(self):
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("APScheduler started.")

    def shutdown(self):
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("APScheduler shut down.")

    def add_cron_job(self, job_id: str, func, cron_expression: str, args: list = None, kwargs: dict = None):
        trigger = CronTrigger.from_crontab(cron_expression)
        self.scheduler.add_job(
            func,
            trigger=trigger,
            id=job_id,
            args=args or [],
            kwargs=kwargs or {},
            replace_existing=True,
        )
