"""Pydantic models for streaming events and aggregated responses."""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class MethodsPayload(BaseModel):
    # Docs
    get_name_doc: str = ""
    get_type_doc: str = ""
    build_circuit_doc: str = ""
    validate_params_doc: str = ""

    # Results
    get_name_result: Optional[str] = None
    get_type_result: Optional[str] = None
    build_circuit_summary: Optional[str] = None
    build_circuit_type: Optional[str] = None

    # Errors
    get_name_error: Optional[str] = None
    get_type_error: Optional[str] = None
    build_circuit_error: Optional[str] = None
    validate_params_error: Optional[str] = None


class AlgorithmResponse(BaseModel):
    class_: str = Field(alias="class")
    class_doc: str
    methods: MethodsPayload
    # Free-form analysis payload as provided by server
    analysis: Optional[Dict[str, Any]] = None

    class Config:
        populate_by_name = True


class StreamEvent(BaseModel):
    type: Literal["start", "status", "error", "result", "done"]
    # Optional shared fields
    message: Optional[str] = None
    stage: Optional[str] = None
    error: Optional[str] = None
    result: Optional[Any] = None
    summary: Optional[Any] = None
    obj_type: Optional[str] = None
    response: Optional[AlgorithmResponse] = None
    class_field: Optional[str] = Field(default=None, alias="class")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class TranscriptEvent(BaseModel):
    """A serializable transcript event that preserves the raw payload and timing."""
    event: StreamEvent


class AlgorithmTranscript(BaseModel):
    """Aggregated transcript for a streaming run."""
    events: List[TranscriptEvent] = Field(default_factory=list)
    response: Optional[AlgorithmResponse] = None
    methods: MethodsPayload = Field(default_factory=MethodsPayload)
    class_name: Optional[str] = None
    class_doc: Optional[str] = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    ended_reason: Optional[Literal["done", "error", "client_abort"]] = None

    def add_event(self, e: StreamEvent) -> None:
        self.events.append(TranscriptEvent(event=e))
        if e.type == "result" and e.response is not None:
            self.response = e.response
            # Sync top-level fields
            self.methods = e.response.methods
            self.class_name = e.response.class_
            self.class_doc = e.response.class_doc

    def to_jsonable(self) -> Dict[str, Any]:
        return self.model_dump(by_alias=True)


