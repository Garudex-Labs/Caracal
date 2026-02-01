"""
Ledger management for Caracal Core.

This module provides the LedgerWriter for appending events to an immutable ledger
and LedgerQuery for querying ledger events.
"""

import fcntl
import json
import os
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Optional

from caracal.exceptions import (
    FileReadError,
    FileWriteError,
    InvalidLedgerEventError,
    LedgerReadError,
    LedgerWriteError,
)
from caracal.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class LedgerEvent:
    """
    Represents a single event in the immutable ledger.
    
    This is compatible with ASE protocol ChargeEvent structure but simplified
    for v0.1 MVP with file-based storage.
    
    Attributes:
        event_id: Monotonically increasing event ID
        agent_id: Agent identifier
        timestamp: ISO 8601 timestamp
        resource_type: Type of resource consumed (e.g., "openai.gpt4.input_tokens")
        quantity: Amount of resource consumed (as string for precision)
        cost: Calculated cost (as string for precision)
        currency: Currency code (e.g., "USD")
        metadata: Optional additional context
    """
    event_id: int
    agent_id: str
    timestamp: str  # ISO 8601 format
    resource_type: str
    quantity: str  # Decimal as string for precision
    cost: str  # Decimal as string for precision
    currency: str
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        # Remove None metadata to keep JSON clean
        if data.get('metadata') is None:
            data.pop('metadata', None)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LedgerEvent":
        """Create LedgerEvent from dictionary."""
        return cls(**data)

    def to_json_line(self) -> str:
        """Convert to JSON Lines format (single line JSON)."""
        return json.dumps(self.to_dict(), separators=(',', ':'))


class LedgerWriter:
    """
    Manages appending events to the immutable ledger.
    
    Implements:
    - Append-only semantics (no updates or deletes)
    - Monotonically increasing event IDs
    - JSON Lines format (one JSON object per line)
    - File locking for concurrent safety
    - Atomic write operations
    - Rolling backups
    """

    def __init__(self, ledger_path: str, backup_count: int = 3):
        """
        Initialize LedgerWriter.
        
        Args:
            ledger_path: Path to the ledger file (JSON Lines format)
            backup_count: Number of rolling backups to maintain (default: 3)
        """
        self.ledger_path = Path(ledger_path)
        self.backup_count = backup_count
        self._next_event_id = 1
        self._backup_created = False
        
        # Ensure parent directory exists
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create ledger file if it doesn't exist
        if not self.ledger_path.exists():
            self.ledger_path.touch()
            logger.info(f"Created new ledger file at {self.ledger_path}")
        else:
            # Load existing ledger to determine next event ID
            self._initialize_event_id()
            logger.info(f"Loaded existing ledger from {self.ledger_path}, next event ID: {self._next_event_id}")

    def append_event(
        self,
        agent_id: str,
        resource_type: str,
        quantity: Decimal,
        cost: Decimal,
        currency: str = "USD",
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ) -> LedgerEvent:
        """
        Append an event to the ledger.
        
        This method is thread-safe and uses file locking to prevent concurrent writes.
        Writes are flushed immediately to ensure durability.
        
        Args:
            agent_id: Agent identifier
            resource_type: Type of resource consumed
            quantity: Amount of resource consumed
            cost: Calculated cost
            currency: Currency code (default: "USD")
            metadata: Optional additional context
            timestamp: Optional timestamp (defaults to current UTC time)
            
        Returns:
            LedgerEvent: The created ledger event
            
        Raises:
            LedgerWriteError: If write operation fails
            InvalidLedgerEventError: If event data is invalid
        """
        # Validate inputs
        if not agent_id:
            raise InvalidLedgerEventError("agent_id cannot be empty")
        if not resource_type:
            raise InvalidLedgerEventError("resource_type cannot be empty")
        if quantity < 0:
            raise InvalidLedgerEventError(f"quantity must be non-negative, got {quantity}")
        if cost < 0:
            raise InvalidLedgerEventError(f"cost must be non-negative, got {cost}")
        
        # Create backup on first write (if not already created)
        if not self._backup_created and self.ledger_path.exists() and self.ledger_path.stat().st_size > 0:
            self._create_backup()
            self._backup_created = True
        
        # Use provided timestamp or current UTC time
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        # Create ledger event
        event = LedgerEvent(
            event_id=self._get_next_event_id(),
            agent_id=agent_id,
            timestamp=timestamp.isoformat() + "Z",
            resource_type=resource_type,
            quantity=str(quantity),
            cost=str(cost),
            currency=currency,
            metadata=metadata,
        )
        
        # Write to ledger with file locking
        try:
            self._atomic_append(event)
            logger.info(
                f"Ledger write: event_id={event.event_id}, agent_id={agent_id}, "
                f"resource={resource_type}, cost={cost} {currency}"
            )
            return event
        except Exception as e:
            raise LedgerWriteError(
                f"Failed to append event to ledger {self.ledger_path}: {e}"
            ) from e

    def _atomic_append(self, event: LedgerEvent) -> None:
        """
        Perform atomic append operation with file locking.
        
        Steps:
        1. Acquire exclusive file lock
        2. Append event as JSON line
        3. Flush write buffer to OS
        4. Force OS to write to physical disk (fsync)
        5. Release file lock
        
        Args:
            event: LedgerEvent to append
            
        Raises:
            LedgerWriteError: If write operation fails
        """
        try:
            # Open file in append mode
            with open(self.ledger_path, 'a') as f:
                # Acquire exclusive lock (blocks until available)
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                
                try:
                    # Write event as JSON line
                    json_line = event.to_json_line()
                    f.write(json_line + '\n')
                    
                    # Flush write buffer to OS
                    f.flush()
                    
                    # Force OS to write to physical disk
                    os.fsync(f.fileno())
                    
                finally:
                    # Release lock (automatically released on close, but explicit is better)
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                    
        except Exception as e:
            raise LedgerWriteError(
                f"Failed to perform atomic append to {self.ledger_path}: {e}"
            ) from e

    def _get_next_event_id(self) -> int:
        """
        Get the next monotonically increasing event ID.
        
        Returns:
            int: Next event ID
        """
        event_id = self._next_event_id
        self._next_event_id += 1
        return event_id

    def _initialize_event_id(self) -> None:
        """
        Initialize the next event ID by reading the last event from the ledger.
        
        This is called when loading an existing ledger to ensure event IDs
        continue monotonically increasing.
        """
        try:
            # Read the last line of the ledger file
            with open(self.ledger_path, 'rb') as f:
                # Seek to end of file
                f.seek(0, os.SEEK_END)
                file_size = f.tell()
                
                if file_size == 0:
                    # Empty file, start at 1
                    self._next_event_id = 1
                    return
                
                # Read backwards to find the last line
                # Start with a reasonable buffer size
                buffer_size = min(8192, file_size)
                f.seek(max(0, file_size - buffer_size))
                
                # Read the buffer and find the last complete line
                buffer = f.read().decode('utf-8')
                lines = buffer.strip().split('\n')
                
                # Get the last non-empty line
                last_line = None
                for line in reversed(lines):
                    if line.strip():
                        last_line = line
                        break
                
                if last_line:
                    # Parse the last event to get its ID
                    last_event_data = json.loads(last_line)
                    last_event_id = last_event_data.get('event_id', 0)
                    self._next_event_id = last_event_id + 1
                else:
                    # No valid events found, start at 1
                    self._next_event_id = 1
                    
        except Exception as e:
            # If we can't read the file, log warning and start at 1
            logger.warning(
                f"Failed to initialize event ID from ledger {self.ledger_path}: {e}. "
                f"Starting at event_id=1"
            )
            self._next_event_id = 1

    def _create_backup(self) -> None:
        """
        Create rolling backup of ledger file.
        
        Rotates backups:
        - ledger.jsonl.bak.3 -> deleted
        - ledger.jsonl.bak.2 -> ledger.jsonl.bak.3
        - ledger.jsonl.bak.1 -> ledger.jsonl.bak.2
        - ledger.jsonl -> ledger.jsonl.bak.1
        
        This is called on system startup before the first write.
        """
        if not self.ledger_path.exists():
            return
        
        try:
            # Delete oldest backup if it exists
            oldest_backup = Path(f"{self.ledger_path}.bak.{self.backup_count}")
            if oldest_backup.exists():
                oldest_backup.unlink()
            
            # Rotate existing backups (from newest to oldest)
            for i in range(self.backup_count - 1, 0, -1):
                old_backup = Path(f"{self.ledger_path}.bak.{i}")
                new_backup = Path(f"{self.ledger_path}.bak.{i + 1}")
                
                if old_backup.exists():
                    old_backup.rename(new_backup)
            
            # Create new backup
            backup_path = Path(f"{self.ledger_path}.bak.1")
            shutil.copy2(self.ledger_path, backup_path)
            
            logger.info(f"Created ledger backup at {backup_path}")
            
        except Exception as e:
            # Log warning but don't fail the operation
            # Backup failure shouldn't prevent writes
            logger.warning(f"Failed to create backup of ledger: {e}")
