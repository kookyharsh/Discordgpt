# Job Scheduler Architecture

- **Engine**: BullMQ backed by Redis with PostgreSQL durable storage.
- **Safety**: Scheduled actions store `createdByUserId` and re-evaluate permissions, role hierarchy, and server policies at execution time.
