"""AI Call Analytics — API Schemas."""

from backend.app.schemas.analysis import (
    AnalysisStatusResponse,
    AnalysisSummaryResponse,
    StartAnalysisRequest,
)
from backend.app.schemas.auth import (
    CompanyCreate,
    CompanyResponse,
    LoginRequest,
    RegisterRequest,
    TokenPayload,
    TokenResponse,
    UserResponse,
)
from backend.app.schemas.batch import (
    BatchDetailResponse,
    BatchListResponse,
    BatchResponse,
)
from backend.app.schemas.call import (
    AudioFileResponse,
    BulkIngestResponse,
    CallCreate,
    CallDetailResponse,
    CallListResponse,
    CallResponse,
    SkippedFileInfo,
)
from backend.app.schemas.common import ErrorDetail, ErrorResponse, PaginationMeta
from backend.app.schemas.job import JobListResponse, JobResponse
from backend.app.schemas.report import (
    ReportGenerateRequest,
    ReportListResponse,
    ReportResponse,
)
from backend.app.schemas.risk import EscalationRiskResponse
from backend.app.schemas.search import (
    SearchResultItem,
    SemanticSearchRequest,
    SemanticSearchResponse,
)
from backend.app.schemas.theme import ThemeItemResponse, ThemeListResponse
from backend.app.schemas.transcript import (
    TranscriptResponse,
    TranscriptTurnListResponse,
    TranscriptTurnResponse,
)

__all__ = [
    "PaginationMeta",
    "ErrorDetail",
    "ErrorResponse",
    "CallCreate",
    "CallResponse",
    "CallDetailResponse",
    "CallListResponse",
    "AudioFileResponse",
    "TranscriptResponse",
    "TranscriptTurnResponse",
    "TranscriptTurnListResponse",
    "StartAnalysisRequest",
    "AnalysisStatusResponse",
    "AnalysisSummaryResponse",
    "SemanticSearchRequest",
    "SearchResultItem",
    "SemanticSearchResponse",
    "ThemeItemResponse",
    "ThemeListResponse",
    "EscalationRiskResponse",
    "JobResponse",
    "JobListResponse",
    "CompanyCreate",
    "CompanyResponse",
    "RegisterRequest",
    "LoginRequest",
    "UserResponse",
    "TokenResponse",
    "TokenPayload",
    "BulkIngestResponse",
    "SkippedFileInfo",
    "ReportGenerateRequest",
    "ReportResponse",
    "ReportListResponse",
    "BatchResponse",
    "BatchDetailResponse",
    "BatchListResponse",
]
