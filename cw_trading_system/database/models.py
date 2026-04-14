# cw_trading_system/database/models.py

from sqlalchemy import (
    Column, String, Float, Integer, DateTime, Boolean, 
    ForeignKey, Enum, Text, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from . import Base


# =========================
# ENUMS
# =========================

class PositionStatus(str, enum.Enum):
    """Status of a position."""
    ACTIVE = "active"
    CLOSED = "closed"
    EXPIRED = "expired"
    EXERCISED = "exercised"


class TradeAction(str, enum.Enum):
    """Type of trade action."""
    SELL = "sell"  # CW issuance
    BUY = "buy"    # CW buyback
    HEDGE_BUY = "hedge_buy"
    HEDGE_SELL = "hedge_sell"


class AuditEventType(str, enum.Enum):
    """Type of audit event."""
    POSITION_CREATED = "position_created"
    POSITION_UPDATED = "position_updated"
    POSITION_DELETED = "position_deleted"
    POSITION_CLOSED = "position_closed"
    TRADE_EXECUTED = "trade_executed"
    TRADE_FAILED = "trade_failed"
    RISK_LIMIT_BREACH = "risk_limit_breach"
    MARKET_DATA_UPDATE = "market_data_update"
    RECONCILIATION = "reconciliation"
    MANUAL_ADJUSTMENT = "manual_adjustment"
    SYSTEM_EVENT = "system_event"


# =========================
# CW POSITION MODEL
# =========================

class CWPosition(Base):
    """
    Covered Warrant position.
    Represents a long position in issued CWs with hedge tracking.
    """
    __tablename__ = "cw_positions"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Core position data
    underlying = Column(String(20), nullable=False, index=True)
    ticker = Column(String(20), nullable=False, index=True)
    cw_qty = Column(Integer, nullable=False, default=0)
    conversion_ratio = Column(Float, nullable=False)
    strike = Column(Float, nullable=False)
    expiry = Column(String(10), nullable=False)  # ISO format: YYYY-MM-DD
    issue_price = Column(Float, nullable=False)
    sigma = Column(Float, nullable=False)  # Historical volatility
    
    # Position status
    status = Column(
        Enum(PositionStatus),
        nullable=False,
        default=PositionStatus.ACTIVE,
        index=True
    )
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)
    
    # Audit fields
    created_by = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    trades = relationship(
        "Trade",
        back_populates="cw_position",
        cascade="all, delete-orphan",
        foreign_keys="Trade.cw_position_id"
    )
    audit_events = relationship(
        "AuditEvent",
        back_populates="cw_position",
        cascade="all, delete-orphan",
        foreign_keys="AuditEvent.cw_position_id"
    )
    snapshots = relationship(
        "MonitorSnapshot",
        back_populates="cw_position",
        cascade="all, delete-orphan",
        foreign_keys="MonitorSnapshot.cw_position_id"
    )
    
    # Constraints
    __table_args__ = (
        Index("idx_cw_underlying_status", "underlying", "status"),
        Index("idx_cw_expiry", "expiry"),
        Index("idx_cw_created_at", "created_at"),
    )
    
    def __repr__(self):
        return (
            f"<CWPosition(id={self.id}, underlying={self.underlying}, "
            f"cw_qty={self.cw_qty}, strike={self.strike}, expiry={self.expiry}, "
            f"status={self.status})>"
        )


# =========================
# HEDGE POSITION MODEL
# =========================

class HedgePosition(Base):
    """
    Hedge position (equity hedge for CW delta).
    Represents shares held to hedge the portfolio delta.
    """
    __tablename__ = "hedge_positions"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Core position data
    underlying = Column(String(20), nullable=False, unique=True, index=True)
    shares = Column(Integer, nullable=False, default=0)
    avg_price = Column(Float, nullable=False, default=0.0)
    
    # Position tracking
    total_cost = Column(Float, nullable=False, default=0.0)
    status = Column(
        Enum(PositionStatus),
        nullable=False,
        default=PositionStatus.ACTIVE,
        index=True
    )
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Audit fields
    created_by = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    trades = relationship(
        "Trade",
        back_populates="hedge_position",
        cascade="all, delete-orphan",
        foreign_keys="Trade.hedge_position_id"
    )
    audit_events = relationship(
        "AuditEvent",
        back_populates="hedge_position",
        cascade="all, delete-orphan",
        foreign_keys="AuditEvent.hedge_position_id"
    )
    
    # Constraints
    __table_args__ = (
        Index("idx_hedge_status", "status"),
        Index("idx_hedge_created_at", "created_at"),
    )
    
    def __repr__(self):
        return (
            f"<HedgePosition(id={self.id}, underlying={self.underlying}, "
            f"shares={self.shares}, avg_price={self.avg_price})>"
        )


# =========================
# TRADE MODEL
# =========================

class Trade(Base):
    """
    Trade execution record.
    Records all executed trades: CW issuances, buybacks, and hedge trades.
    """
    __tablename__ = "trades"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Trade identification
    trade_id = Column(String(50), nullable=True, unique=True, index=True)
    action = Column(Enum(TradeAction), nullable=False, index=True)
    
    # Trade details
    underlying = Column(String(20), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    execution_time = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Trade cost/PnL
    trade_value = Column(Float, nullable=False)
    fees = Column(Float, nullable=False, default=0.0)
    notional_value = Column(Float, nullable=False)
    
    # Trade status
    status = Column(String(20), nullable=False, default="filled")
    
    # Position references
    cw_position_id = Column(Integer, ForeignKey("cw_positions.id"), nullable=True)
    hedge_position_id = Column(Integer, ForeignKey("hedge_positions.id"), nullable=True)
    
    # Counterparty / Broker
    counterparty = Column(String(100), nullable=True)
    broker_trade_id = Column(String(100), nullable=True)
    
    # Audit fields
    created_by = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    cw_position = relationship(
        "CWPosition",
        back_populates="trades",
        foreign_keys=[cw_position_id]
    )
    hedge_position = relationship(
        "HedgePosition",
        back_populates="trades",
        foreign_keys=[hedge_position_id]
    )
    audit_events = relationship(
        "AuditEvent",
        back_populates="trade",
        cascade="all, delete-orphan"
    )
    
    # Constraints
    __table_args__ = (
        Index("idx_trade_action_time", "action", "execution_time"),
        Index("idx_trade_status", "status"),
        Index("idx_trade_underlying", "underlying"),
    )
    
    def __repr__(self):
        return (
            f"<Trade(id={self.id}, action={self.action}, underlying={self.underlying}, "
            f"quantity={self.quantity}, price={self.price})>"
        )


# =========================
# MONITOR SNAPSHOT MODEL
# =========================

class MonitorSnapshot(Base):
    """
    Risk and P&L snapshot.
    Time-series snapshot of Greeks, P&L, and risk metrics at a point in time.
    """
    __tablename__ = "monitor_snapshots"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Timestamp
    snapshot_time = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Greeks (portfolio-level)
    delta = Column(Float, nullable=False, default=0.0)
    gamma = Column(Float, nullable=False, default=0.0)
    vega = Column(Float, nullable=False, default=0.0)
    theta = Column(Float, nullable=False, default=0.0)
    rho = Column(Float, nullable=False, default=0.0)
    
    # P&L
    total_pnl = Column(Float, nullable=False, default=0.0)
    realized_pnl = Column(Float, nullable=False, default=0.0)
    unrealized_pnl = Column(Float, nullable=False, default=0.0)
    
    # Market data snapshot
    spot_price = Column(Float, nullable=True)
    implied_vol = Column(Float, nullable=True)
    
    # Position references (optional, for disaggregated snapshots)
    cw_position_id = Column(Integer, ForeignKey("cw_positions.id"), nullable=True)
    hedge_position_id = Column(Integer, ForeignKey("hedge_positions.id"), nullable=True)
    
    # Metadata
    data_source = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    cw_position = relationship(
        "CWPosition",
        back_populates="snapshots",
        foreign_keys=[cw_position_id]
    )
    hedge_position = relationship(
        "HedgePosition",
        foreign_keys=[hedge_position_id]
    )
    
    # Constraints
    __table_args__ = (
        Index("idx_snapshot_time", "snapshot_time"),
        Index("idx_snapshot_cw_position", "cw_position_id", "snapshot_time"),
        Index("idx_snapshot_created", "created_at"),
    )
    
    def __repr__(self):
        return (
            f"<MonitorSnapshot(id={self.id}, snapshot_time={self.snapshot_time}, "
            f"delta={self.delta}, gamma={self.gamma}, total_pnl={self.total_pnl})>"
        )


# =========================
# AUDIT EVENT MODEL
# =========================

class AuditEvent(Base):
    """
    Audit trail for compliance.
    Records all mutations and significant system events with full context.
    """
    __tablename__ = "audit_events"
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Event identification
    event_type = Column(Enum(AuditEventType), nullable=False, index=True)
    severity = Column(String(20), nullable=False, default="info")
    
    # Entity references
    cw_position_id = Column(Integer, ForeignKey("cw_positions.id"), nullable=True)
    hedge_position_id = Column(Integer, ForeignKey("hedge_positions.id"), nullable=True)
    trade_id = Column(Integer, ForeignKey("trades.id"), nullable=True)
    
    # Event details
    summary = Column(String(500), nullable=False)
    details = Column(Text, nullable=True)
    
    # Actor
    user = Column(String(100), nullable=True)
    system_component = Column(String(100), nullable=True)
    
    # Status for events that track processes
    status = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    event_time = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    cw_position = relationship(
        "CWPosition",
        back_populates="audit_events",
        foreign_keys=[cw_position_id]
    )
    hedge_position = relationship(
        "HedgePosition",
        back_populates="audit_events",
        foreign_keys=[hedge_position_id]
    )
    trade = relationship(
        "Trade",
        back_populates="audit_events",
        foreign_keys=[trade_id]
    )
    
    # Constraints
    __table_args__ = (
        Index("idx_audit_event_type_time", "event_type", "event_time"),
        Index("idx_audit_severity_time", "severity", "event_time"),
        Index("idx_audit_cw_position", "cw_position_id", "event_time"),
        Index("idx_audit_user_time", "user", "event_time"),
    )
    
    def __repr__(self):
        return (
            f"<AuditEvent(id={self.id}, event_type={self.event_type}, "
            f"severity={self.severity}, summary={self.summary})>"
        )
