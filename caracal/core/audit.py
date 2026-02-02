"""
Audit Log Management for Caracal Core v0.3.

Provides functionality for querying and exporting audit logs in multiple formats.

Requirements: 17.5, 17.7
"""

import csv
import json
import io
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from caracal.db.models import AuditLog
from caracal.db.connection import get_session
from caracal.logging_config import get_logger

logger = get_logger(__name__)


class AuditLogManager:
    """
    Manager for audit log queries and exports.
    
    Provides:
    - Query audit logs by agent, time range, event type, correlation ID
    - Export audit logs in JSON, CSV, and SYSLOG formats
    
    Requirements: 17.5, 17.7
    """
    
    def __init__(self, db_session_factory=None):
        """
        Initialize audit log manager.
        
        Args:
            db_session_factory: Database session factory (defaults to get_session)
        """
        self.db_session_factory = db_session_factory or get_session
    
    def query_audit_logs(
        self,
        agent_id: Optional[UUID] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        event_type: Optional[str] = None,
        correlation_id: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> List[AuditLog]:
        """
        Query audit logs with filters.
        
        Args:
            agent_id: Filter by agent ID
            start_time: Filter by start time (inclusive)
            end_time: Filter by end time (inclusive)
            event_type: Filter by event type
            correlation_id: Filter by correlation ID
            limit: Maximum number of results (default 1000)
            offset: Offset for pagination (default 0)
            
        Returns:
            List of AuditLog entries matching filters
            
        Requirements: 17.7
        """
        with self.db_session_factory() as session:
            query = session.query(AuditLog)
            
            # Apply filters
            filters = []
            
            if agent_id:
                filters.append(AuditLog.agent_id == agent_id)
            
            if start_time:
                filters.append(AuditLog.event_timestamp >= start_time)
            
            if end_time:
                filters.append(AuditLog.event_timestamp <= end_time)
            
            if event_type:
                filters.append(AuditLog.event_type == event_type)
            
            if correlation_id:
                filters.append(AuditLog.correlation_id == correlation_id)
            
            if filters:
                query = query.filter(and_(*filters))
            
            # Order by timestamp descending (most recent first)
            query = query.order_by(AuditLog.event_timestamp.desc())
            
            # Apply pagination
            query = query.limit(limit).offset(offset)
            
            # Execute query
            results = query.all()
            
            logger.info(
                f"Audit log query executed: agent_id={agent_id}, "
                f"start_time={start_time}, end_time={end_time}, "
                f"event_type={event_type}, correlation_id={correlation_id}, "
                f"results={len(results)}"
            )
            
            return results
    
    def export_json(
        self,
        agent_id: Optional[UUID] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        event_type: Optional[str] = None,
        correlation_id: Optional[str] = None,
        limit: int = 10000,
    ) -> str:
        """
        Export audit logs as JSON.
        
        Args:
            agent_id: Filter by agent ID
            start_time: Filter by start time (inclusive)
            end_time: Filter by end time (inclusive)
            event_type: Filter by event type
            correlation_id: Filter by correlation ID
            limit: Maximum number of results (default 10000)
            
        Returns:
            JSON string containing audit log entries
            
        Requirements: 17.5
        """
        logs = self.query_audit_logs(
            agent_id=agent_id,
            start_time=start_time,
            end_time=end_time,
            event_type=event_type,
            correlation_id=correlation_id,
            limit=limit,
        )
        
        # Convert to JSON-serializable format
        export_data = []
        for log in logs:
            entry = {
                "log_id": log.log_id,
                "event_id": log.event_id,
                "event_type": log.event_type,
                "topic": log.topic,
                "partition": log.partition,
                "offset": log.offset,
                "event_timestamp": log.event_timestamp.isoformat(),
                "logged_at": log.logged_at.isoformat(),
                "agent_id": str(log.agent_id) if log.agent_id else None,
                "correlation_id": log.correlation_id,
                "event_data": log.event_data,
            }
            export_data.append(entry)
        
        logger.info(f"Exported {len(export_data)} audit logs as JSON")
        
        return json.dumps(export_data, indent=2)
    
    def export_csv(
        self,
        agent_id: Optional[UUID] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        event_type: Optional[str] = None,
        correlation_id: Optional[str] = None,
        limit: int = 10000,
    ) -> str:
        """
        Export audit logs as CSV.
        
        Args:
            agent_id: Filter by agent ID
            start_time: Filter by start time (inclusive)
            end_time: Filter by end time (inclusive)
            event_type: Filter by event type
            correlation_id: Filter by correlation ID
            limit: Maximum number of results (default 10000)
            
        Returns:
            CSV string containing audit log entries
            
        Requirements: 17.5
        """
        logs = self.query_audit_logs(
            agent_id=agent_id,
            start_time=start_time,
            end_time=end_time,
            event_type=event_type,
            correlation_id=correlation_id,
            limit=limit,
        )
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            "log_id",
            "event_id",
            "event_type",
            "topic",
            "partition",
            "offset",
            "event_timestamp",
            "logged_at",
            "agent_id",
            "correlation_id",
            "event_data_json",
        ])
        
        # Write rows
        for log in logs:
            writer.writerow([
                log.log_id,
                log.event_id,
                log.event_type,
                log.topic,
                log.partition,
                log.offset,
                log.event_timestamp.isoformat(),
                log.logged_at.isoformat(),
                str(log.agent_id) if log.agent_id else "",
                log.correlation_id or "",
                json.dumps(log.event_data),
            ])
        
        csv_content = output.getvalue()
        output.close()
        
        logger.info(f"Exported {len(logs)} audit logs as CSV")
        
        return csv_content
    
    def export_syslog(
        self,
        agent_id: Optional[UUID] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        event_type: Optional[str] = None,
        correlation_id: Optional[str] = None,
        limit: int = 10000,
        facility: int = 16,  # Local0
        severity: int = 6,   # Informational
    ) -> str:
        """
        Export audit logs in SYSLOG format (RFC 5424).
        
        Args:
            agent_id: Filter by agent ID
            start_time: Filter by start time (inclusive)
            end_time: Filter by end time (inclusive)
            event_type: Filter by event type
            correlation_id: Filter by correlation ID
            limit: Maximum number of results (default 10000)
            facility: Syslog facility code (default 16 = Local0)
            severity: Syslog severity level (default 6 = Informational)
            
        Returns:
            SYSLOG formatted string containing audit log entries
            
        Requirements: 17.5
        """
        logs = self.query_audit_logs(
            agent_id=agent_id,
            start_time=start_time,
            end_time=end_time,
            event_type=event_type,
            correlation_id=correlation_id,
            limit=limit,
        )
        
        # Calculate priority (facility * 8 + severity)
        priority = facility * 8 + severity
        
        # Build SYSLOG messages
        syslog_lines = []
        
        for log in logs:
            # Format timestamp in RFC 3339 format
            timestamp = log.event_timestamp.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            
            # Build structured data
            structured_data = (
                f'[caracal@32473 '
                f'log_id="{log.log_id}" '
                f'event_id="{log.event_id}" '
                f'event_type="{log.event_type}" '
                f'topic="{log.topic}" '
                f'partition="{log.partition}" '
                f'offset="{log.offset}"'
            )
            
            if log.agent_id:
                structured_data += f' agent_id="{log.agent_id}"'
            
            if log.correlation_id:
                structured_data += f' correlation_id="{log.correlation_id}"'
            
            structured_data += ']'
            
            # Build message
            event_data_json = json.dumps(log.event_data)
            message = f"Caracal audit event: {event_data_json}"
            
            # Build SYSLOG line (RFC 5424 format)
            # <priority>version timestamp hostname app-name procid msgid structured-data message
            syslog_line = (
                f"<{priority}>1 {timestamp} caracal-core audit-logger - - "
                f"{structured_data} {message}"
            )
            
            syslog_lines.append(syslog_line)
        
        syslog_content = "\n".join(syslog_lines)
        
        logger.info(f"Exported {len(logs)} audit logs as SYSLOG")
        
        return syslog_content
