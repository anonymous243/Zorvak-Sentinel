import asyncio
import logging
import os
from typing import Protocol

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from sentinel_core import outbox_service
from sentinel_core.models import OutboxEvent

logger = logging.getLogger(__name__)

SENTINEL_OUTBOX_POLL_INTERVAL_SECONDS = float(os.getenv("SENTINEL_OUTBOX_POLL_INTERVAL_SECONDS", "1.0"))
SENTINEL_OUTBOX_BATCH_SIZE = int(os.getenv("SENTINEL_OUTBOX_BATCH_SIZE", "50"))

class EventPublisher(Protocol):
    """
    Protocol for publishing outbox events externally.
    
    The dispatcher must not know the specifics of the external system
    (HTTP, Kafka, etc.). The publisher handles the actual delivery.
    """
    async def publish(self, event: OutboxEvent) -> None:
        ...


class OutboxDispatcher:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        publisher: EventPublisher,
        poll_interval: float = SENTINEL_OUTBOX_POLL_INTERVAL_SECONDS,
        batch_size: int = SENTINEL_OUTBOX_BATCH_SIZE,
    ):
        self.session_factory = session_factory
        self.publisher = publisher
        self.poll_interval = poll_interval
        self.batch_size = batch_size
        self._stop_event = asyncio.Event()

    async def run(self) -> None:
        """
        Run the dispatcher loop until cancelled or stopped.
        """
        logger.info("Outbox dispatcher starting up.")
        try:
            while not self._stop_event.is_set():
                processed_count = await self.process_batch()
                
                if processed_count == 0:
                    # No events were claimed, sleep for the poll interval
                    try:
                        await asyncio.wait_for(self._stop_event.wait(), timeout=self.poll_interval)
                    except asyncio.TimeoutError:
                        pass
                    
                # Recover any expired leases periodically (could also be a separate task, 
                # but doing it here is acceptable and coordinates with the main loop)
                try:
                    async with self.session_factory() as session:
                        recovered = await outbox_service.reclaim_expired_events(session, limit=self.batch_size)
                        if recovered > 0:
                            logger.info(f"Reclaimed {recovered} expired event leases.")
                        await session.commit()
                except Exception as e:
                    logger.error(f"Failed to reclaim expired events: {e}")
                    
        except asyncio.CancelledError:
            logger.info("Outbox dispatcher cancelled via async cancellation.")
        finally:
            logger.info("Outbox dispatcher shutting down.")

    def stop(self) -> None:
        """
        Signal the dispatcher to stop gracefully.
        """
        self._stop_event.set()

    async def process_batch(self) -> int:
        """
        Claim a batch of events and process them.
        Returns the number of events claimed.
        """
        events = []
        claim_token = None
        
        # 1. Obtain a fresh database session and claim a bounded batch.
        try:
            async with self.session_factory() as session:
                events, claim_token = await outbox_service.claim_events(session, batch_size=self.batch_size)
                # 3. Commit the claim transaction.
                await session.commit()
        except Exception as e:
            logger.error(f"Database failure during claim_events: {e}")
            return 0

        if not events or not claim_token:
            return 0

        logger.info(f"Claimed {len(events)} events with token {claim_token}.")

        # 4. Publish each claimed event externally.
        for event in events:
            if self._stop_event.is_set():
                break
                
            try:
                # The publisher receives the immutable event.
                await self.publisher.publish(event)
                
                # 5. Successful publication.
                try:
                    async with self.session_factory() as session:
                        success = await outbox_service.mark_published(session, event.id, claim_token)
                        if success:
                            logger.info(f"Successfully published and marked event {event.id}.")
                        else:
                            logger.warning(f"Failed to mark event {event.id} as published (stale ownership).")
                        await session.commit()
                except Exception as e:
                    logger.error(f"Database failure marking event {event.id} published: {e}")
                    # We intentionally do not swallow this failure and pretend it succeeded.
                    
            except Exception as pub_error:
                # 6. Publication failure.
                logger.warning(f"Failed to publish event {event.id}: {pub_error}")
                try:
                    async with self.session_factory() as session:
                        success = await outbox_service.mark_failed(
                            session, event.id, claim_token, str(pub_error)
                        )
                        if not success:
                            logger.warning(f"Failed to mark event {event.id} as failed (stale ownership).")
                        await session.commit()
                except Exception as e:
                    logger.error(f"Database failure marking event {event.id} failed: {e}")

        return len(events)
