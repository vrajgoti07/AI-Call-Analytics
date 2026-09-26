"""
AI Call Analytics — Enterprise Report Generation Service.

Orchestrates multi-tenant report generation for:
1. Individual Call Intelligence Reports
2. Company-Level Executive Analytics & KPI Reports
3. Date-Range Telemetry Reports

Produces downloadable artifacts in PDF, JSON, and CSV formats.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.exceptions import AppException, CallNotFoundError
from backend.app.models.call import Call, CallStatus
from backend.app.models.company import Company
from backend.app.models.escalation import EscalationRisk
from backend.app.models.report import Report, ReportStatus, ReportType
from backend.app.models.transcript import Transcript
from backend.app.repositories.batch_repository import BatchRepository
from backend.app.repositories.call_repository import CallRepository
from backend.app.repositories.company_repository import CompanyRepository
from backend.app.repositories.report_repository import ReportRepository
from backend.app.repositories.transcript_repository import TranscriptRepository
from backend.app.schemas.report import ReportGenerateRequest

logger = logging.getLogger("backend.app.services.report_service")


def _sanitize_filename(text: str) -> str:
    """Produce safe ASCII filename without path traversal or invalid characters."""
    clean = re.sub(r"[^\w\s-]", "", text.strip().lower())
    clean = re.sub(r"[\s_-]+", "-", clean).strip("-")
    return clean or "report"


def _format_seconds(seconds: float | None) -> str:
    """Format duration in mm:ss format."""
    if seconds is None:
        return "--:--"
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


class ReportService:
    """Service orchestrating analytics compilation and multi-format report generation."""

    @classmethod
    def generate_report(
        cls,
        db: Session,
        company_id: uuid.UUID,
        user_id: uuid.UUID | None,
        req: ReportGenerateRequest,
    ) -> Report:
        """
        Validate permissions, calculate summary analytics, build PDF/JSON/CSV artifacts,
        and persist Report record.
        """
        company = CompanyRepository.get_by_id(db, company_id)
        if not company:
            raise AppException("COMPANY_NOT_FOUND", f"Company {company_id} not found.", 404)

        # Setup directory: data/reports/company_{company_id}/
        base_dir = Path("data") / "reports" / f"company_{company_id}"
        base_dir.mkdir(parents=True, exist_ok=True)

        if req.report_type == ReportType.INDIVIDUAL_CALL.value:
            return cls._generate_individual_call_report(
                db=db,
                company=company,
                user_id=user_id,
                call_id=req.call_id,
                custom_title=req.title,
                output_dir=base_dir,
            )
        elif req.report_type == ReportType.BATCH_ANALYTICS.value or req.batch_id is not None:
            return cls._generate_batch_analytics_report(
                db=db,
                company=company,
                user_id=user_id,
                batch_id=req.batch_id,
                custom_title=req.title,
                output_dir=base_dir,
            )
        else:
            return cls._generate_company_analytics_report(
                db=db,
                company=company,
                user_id=user_id,
                date_from=req.date_from,
                date_to=req.date_to,
                custom_title=req.title,
                output_dir=base_dir,
            )

    @classmethod
    def _generate_individual_call_report(
        cls,
        db: Session,
        company: Company,
        user_id: uuid.UUID | None,
        call_id: uuid.UUID | None,
        custom_title: str | None,
        output_dir: Path,
    ) -> Report:
        """Generate comprehensive individual call report."""
        if not call_id:
            raise AppException(
                "INVALID_REQUEST",
                "call_id is required for INDIVIDUAL_CALL report generation.",
                400,
            )

        call = CallRepository.get_by_id(db, call_id, company_id=company.id)
        if not call:
            raise CallNotFoundError(call_id)

        title = custom_title or f"Call Analysis Report — #{call.external_id or str(call.id)[:8]}"

        report = ReportRepository.create_report(
            db=db,
            company_id=company.id,
            call_id=call.id,
            user_id=user_id,
            title=title,
            report_type=ReportType.INDIVIDUAL_CALL.value,
            status=ReportStatus.GENERATING.value,
        )

        try:
            transcript = TranscriptRepository.get_by_call_id(db, call.id)
            turns = transcript.turns if transcript else []

            # Auto-enrich turns with NLP if sentiment data is missing
            if turns and not any(t.sentiment for t in turns):
                try:
                    from ai_service.diarization.schema import SpeakerAttributedTranscript, SpeakerTurn

                    speaker_turns = [
                        SpeakerTurn(
                            turn_id=t.sequence_number,
                            speaker=t.speaker_id,
                            start=t.start_time,
                            end=t.end_time,
                            text=t.text,
                        )
                        for t in turns
                    ]
                    diarized = SpeakerAttributedTranscript(
                        full_text=transcript.text or "",
                        turns=speaker_turns,
                        speakers=sorted({t.speaker_id for t in turns}),
                        total_turns=len(turns),
                        audio_duration=transcript.duration or call.duration or 15.0,
                    )

                    from ai_service.pipeline.nlp_analyzer import NLPAnalyzer

                    nlp_analyzer = NLPAnalyzer()
                    nlp_result = nlp_analyzer.analyze(diarized)

                    if nlp_result and nlp_result.sentiment:
                        for turn in turns:
                            matching = next(
                                (s for s in nlp_result.sentiment.turns if s.turn_id == turn.sequence_number),
                                None,
                            )
                            if matching:
                                turn.sentiment = {"label": matching.label, "score": float(matching.score)}
                            if nlp_result.intent:
                                turn.intent = {
                                    "intent": nlp_result.intent.predicted_intent,
                                    "confidence": float(nlp_result.intent.confidence),
                                }
                        db.commit()
                        logger.info("Auto-enriched %d turns with NLP data for report generation.", len(turns))

                    # Run risk analysis if not already present
                    try:
                        from ai_service.risk.service import EscalationRiskService

                        risk_svc = EscalationRiskService()
                        risk_svc.analyze(
                            call_id=str(call.id),
                            transcript=diarized,
                            sentiment=nlp_result.sentiment if nlp_result else None,
                            intent=nlp_result.intent if nlp_result else None,
                            entities=nlp_result.entities if nlp_result else None,
                            db_session=db,
                        )
                    except Exception as risk_err:
                        logger.warning("Inline risk analysis skipped: %s", risk_err)

                except Exception as nlp_err:
                    logger.warning("Inline NLP enrichment skipped: %s", nlp_err)

            # Escalation risk
            risk_record = db.scalar(
                select(EscalationRisk)
                .where(EscalationRisk.call_id == str(call.id))
                .order_by(desc(EscalationRisk.created_at))
                .limit(1)
            )

            if not risk_record and turns:
                try:
                    from ai_service.diarization.schema import SpeakerAttributedTranscript, SpeakerTurn
                    from ai_service.risk.service import EscalationRiskService

                    speaker_turns = [
                        SpeakerTurn(
                            turn_id=t.sequence_number,
                            speaker=t.speaker_id,
                            start=t.start_time,
                            end=t.end_time,
                            text=t.text,
                        )
                        for t in turns
                    ]
                    diarized = SpeakerAttributedTranscript(
                        full_text=transcript.text or "",
                        turns=speaker_turns,
                        speakers=sorted({t.speaker_id for t in turns}),
                        total_turns=len(turns),
                        audio_duration=transcript.duration or call.duration or 15.0,
                    )
                    risk_svc = EscalationRiskService()
                    risk_svc.analyze(
                        call_id=str(call.id),
                        transcript=diarized,
                        db_session=db,
                    )
                    db.commit()
                    risk_record = db.scalar(
                        select(EscalationRisk)
                        .where(EscalationRisk.call_id == str(call.id))
                        .order_by(desc(EscalationRisk.created_at))
                        .limit(1)
                    )
                    logger.info("Inline risk analysis evaluated for call %s", call.id)
                except Exception as risk_err:
                    logger.warning("Inline risk analysis fallback failed: %s", risk_err)

            # Metrics
            sentiment_counts: dict[str, int] = {}
            intent_counts: dict[str, int] = {}
            speaker_times: dict[str, float] = {}

            for turn in turns:
                spk = turn.speaker_id
                speaker_times[spk] = speaker_times.get(spk, 0.0) + (turn.end_time - turn.start_time)
                if turn.sentiment and isinstance(turn.sentiment, dict):
                    lbl = turn.sentiment.get("label", "NEUTRAL")
                    sentiment_counts[lbl] = sentiment_counts.get(lbl, 0) + 1
                if turn.intent and isinstance(turn.intent, dict):
                    intent = turn.intent.get("intent", "general_inquiry")
                    intent_counts[intent] = intent_counts.get(intent, 0) + 1

            dominant_sentiment = max(sentiment_counts, key=sentiment_counts.get) if sentiment_counts else "NEUTRAL"
            primary_intent = max(intent_counts, key=intent_counts.get) if intent_counts else "general_inquiry"

            summary_data: dict[str, Any] = {
                "report_id": str(report.id),
                "company_name": company.name,
                "call_id": str(call.id),
                "external_id": call.external_id,
                "call_status": call.status,
                "duration_seconds": call.duration,
                "language": call.language,
                "turn_count": len(turns),
                "speaker_count": len(speaker_times),
                "dominant_sentiment": dominant_sentiment,
                "sentiment_distribution": sentiment_counts,
                "primary_intent": primary_intent,
                "intent_distribution": intent_counts,
                "risk_score": risk_record.risk_score if risk_record else None,
                "risk_level": risk_record.risk_level if risk_record else None,
                "risk_probability": risk_record.risk_probability if risk_record else None,
                "risk_explanation": risk_record.explanation if risk_record else None,
                "top_risk_factors": risk_record.top_factors if risk_record else [],
                "created_at": call.created_at.isoformat(),
            }

            prefix = f"call_{str(call.id)[:8]}_{str(report.id)[:8]}"
            pdf_path = output_dir / f"{prefix}.pdf"
            json_path = output_dir / f"{prefix}.json"
            csv_path = output_dir / f"{prefix}.csv"

            # 1. Write JSON
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(summary_data, f, indent=2)

            # 2. Write CSV (Speaker Turns)
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Turn", "Speaker", "Start (s)", "End (s)", "Text", "Sentiment", "Intent"])
                for idx, t in enumerate(turns, 1):
                    s_lbl = t.sentiment.get("label", "") if t.sentiment and isinstance(t.sentiment, dict) else ""
                    i_lbl = t.intent.get("intent", "") if t.intent and isinstance(t.intent, dict) else ""
                    writer.writerow([idx, t.speaker_id, f"{t.start_time:.2f}", f"{t.end_time:.2f}", t.text, s_lbl, i_lbl])

            # 3. Write PDF
            cls._render_call_pdf(
                output_path=pdf_path,
                company=company,
                call=call,
                summary=summary_data,
                turns=turns,
                risk=risk_record,
            )

            pdf_bytes = pdf_path.read_bytes() if pdf_path.exists() else None

            # Mark completed and persist PDF binary in PostgreSQL
            updated_report = ReportRepository.update_report_completed(
                db=db,
                report_id=report.id,
                file_path_pdf=str(pdf_path),
                file_path_json=str(json_path),
                file_path_csv=str(csv_path),
                summary_data=summary_data,
                pdf_data=pdf_bytes,
            )
            # Return the refreshed report so the API response has status=COMPLETED
            return updated_report or report

        except Exception as exc:
            logger.exception("Failed to generate individual call report %s: %s", report.id, exc)
            ReportRepository.update_report_failed(db, report.id, str(exc))
            raise

    @classmethod
    def _generate_company_analytics_report(
        cls,
        db: Session,
        company: Company,
        user_id: uuid.UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
        custom_title: str | None,
        output_dir: Path,
    ) -> Report:
        """Generate comprehensive company executive analytics report."""
        title = custom_title or f"{company.name} — Executive Call Analytics Report"

        report = ReportRepository.create_report(
            db=db,
            company_id=company.id,
            user_id=user_id,
            title=title,
            report_type=ReportType.COMPANY_ANALYTICS.value,
            date_from=date_from,
            date_to=date_to,
            status=ReportStatus.GENERATING.value,
        )

        try:
            # Query calls for this company
            query = select(Call).where(Call.company_id == company.id)
            if date_from:
                query = query.where(Call.created_at >= date_from)
            if date_to:
                query = query.where(Call.created_at <= date_to)
            query = query.order_by(desc(Call.created_at))

            calls = list(db.scalars(query).all())
            total_calls = len(calls)

            # Aggregations
            status_counts: dict[str, int] = {}
            durations: list[float] = []

            for c in calls:
                status_counts[c.status] = status_counts.get(c.status, 0) + 1
                if c.duration:
                    durations.append(c.duration)

            avg_duration = sum(durations) / len(durations) if durations else 0.0

            # Query risks for these calls
            call_id_strs = [str(c.id) for c in calls]
            risk_counts: dict[str, int] = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
            risk_scores: list[float] = []

            if call_id_strs:
                risks_stmt = (
                    select(EscalationRisk)
                    .where(EscalationRisk.call_id.in_(call_id_strs))
                )
                for r in db.scalars(risks_stmt).all():
                    lvl = (r.risk_level or "LOW").upper()
                    risk_counts[lvl] = risk_counts.get(lvl, 0) + 1
                    risk_scores.append(r.risk_score)

            avg_risk_score = sum(risk_scores) / len(risk_scores) if risk_scores else 0.0

            summary_data: dict[str, Any] = {
                "report_id": str(report.id),
                "company_id": str(company.id),
                "company_name": company.name,
                "company_slug": company.slug,
                "date_from": date_from.isoformat() if date_from else None,
                "date_to": date_to.isoformat() if date_to else None,
                "total_calls": total_calls,
                "status_distribution": status_counts,
                "completed_count": status_counts.get(CallStatus.COMPLETED.value, 0),
                "processing_count": status_counts.get(CallStatus.PROCESSING.value, 0),
                "failed_count": status_counts.get(CallStatus.FAILED.value, 0),
                "average_duration_seconds": round(avg_duration, 1),
                "risk_distribution": risk_counts,
                "average_risk_score": round(avg_risk_score, 2),
                "calls_sample": [
                    {
                        "call_id": str(c.id),
                        "external_id": c.external_id,
                        "status": c.status,
                        "duration": c.duration,
                        "language": c.language,
                        "created_at": c.created_at.isoformat(),
                    }
                    for c in calls[:50]
                ],
            }

            prefix = f"company_{company.slug}_{str(report.id)[:8]}"
            pdf_path = output_dir / f"{prefix}.pdf"
            json_path = output_dir / f"{prefix}.json"
            csv_path = output_dir / f"{prefix}.csv"

            # 1. Write JSON
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(summary_data, f, indent=2)

            # 2. Write CSV
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Call ID", "External ID", "Status", "Duration (s)", "Language", "Created At"])
                for c in calls:
                    writer.writerow([
                        str(c.id),
                        c.external_id or "",
                        c.status,
                        f"{c.duration:.1f}" if c.duration else "",
                        c.language or "en",
                        c.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    ])

            # 3. Write PDF
            cls._render_company_pdf(
                output_path=pdf_path,
                company=company,
                summary=summary_data,
                calls=calls,
            )

            pdf_bytes = pdf_path.read_bytes() if pdf_path.exists() else None

            # Mark completed and persist PDF binary in PostgreSQL
            updated_report = ReportRepository.update_report_completed(
                db=db,
                report_id=report.id,
                file_path_pdf=str(pdf_path),
                file_path_json=str(json_path),
                file_path_csv=str(csv_path),
                summary_data=summary_data,
                pdf_data=pdf_bytes,
            )
            # Return the refreshed report so the API response has status=COMPLETED
            return updated_report or report

        except Exception as exc:
            logger.exception("Failed to generate company analytics report %s: %s", report.id, exc)
            ReportRepository.update_report_failed(db, report.id, str(exc))
            raise

    @classmethod
    def _generate_batch_analytics_report(
        cls,
        db: Session,
        company: Company,
        user_id: uuid.UUID | None,
        batch_id: uuid.UUID | None,
        custom_title: str | None,
        output_dir: Path,
    ) -> Report:
        """Generate comprehensive batch analytics report for a specific ZIP upload."""
        if not batch_id:
            raise AppException("INVALID_REQUEST", "batch_id is required for BATCH_ANALYTICS report generation.", 400)

        batch = BatchRepository.get_by_id(db, batch_id, company_id=company.id)
        if not batch:
            raise AppException("BATCH_NOT_FOUND", f"Batch {batch_id} not found.", 404)

        title = custom_title or f"Batch Report — {batch.display_name or batch.original_filename}"

        report = ReportRepository.create_report(
            db=db,
            company_id=company.id,
            batch_id=batch.id,
            user_id=user_id,
            title=title,
            report_type=ReportType.BATCH_ANALYTICS.value,
            status=ReportStatus.GENERATING.value,
        )

        try:
            # Query calls for this batch
            query = (
                select(Call)
                .where(Call.company_id == company.id, Call.batch_id == batch.id)
                .order_by(desc(Call.created_at))
            )
            calls = list(db.scalars(query).all())
            total_calls = len(calls)

            # Aggregations
            status_counts: dict[str, int] = {}
            durations: list[float] = []

            for c in calls:
                status_counts[c.status] = status_counts.get(c.status, 0) + 1
                if c.duration:
                    durations.append(c.duration)

            avg_duration = sum(durations) / len(durations) if durations else 0.0
            total_duration = sum(durations) if durations else 0.0

            # Query risks for these calls
            call_id_strs = [str(c.id) for c in calls]
            risk_counts: dict[str, int] = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
            risk_scores: list[float] = []

            if call_id_strs:
                risks_stmt = (
                    select(EscalationRisk)
                    .where(EscalationRisk.call_id.in_(call_id_strs))
                )
                for r in db.scalars(risks_stmt).all():
                    lvl = (r.risk_level or "LOW").upper()
                    risk_counts[lvl] = risk_counts.get(lvl, 0) + 1
                    risk_scores.append(r.risk_score)

            avg_risk_score = sum(risk_scores) / len(risk_scores) if risk_scores else 0.0

            summary_data: dict[str, Any] = {
                "report_id": str(report.id),
                "company_id": str(company.id),
                "company_name": company.name,
                "batch_id": str(batch.id),
                "batch_name": batch.display_name,
                "original_filename": batch.original_filename,
                "batch_status": batch.status,
                "total_calls": total_calls,
                "status_distribution": status_counts,
                "completed_count": status_counts.get(CallStatus.COMPLETED.value, 0),
                "processing_count": status_counts.get(CallStatus.PROCESSING.value, 0),
                "failed_count": status_counts.get(CallStatus.FAILED.value, 0),
                "uploaded_count": status_counts.get(CallStatus.UPLOADED.value, 0),
                "average_duration_seconds": round(avg_duration, 1),
                "total_duration_seconds": round(total_duration, 1),
                "risk_distribution": risk_counts,
                "average_risk_score": round(avg_risk_score, 2),
                "calls_sample": [
                    {
                        "call_id": str(c.id),
                        "external_id": c.external_id,
                        "status": c.status,
                        "duration": c.duration,
                        "language": c.language,
                        "created_at": c.created_at.isoformat(),
                    }
                    for c in calls
                ],
            }

            prefix = f"batch_{str(batch.id)[:8]}_{str(report.id)[:8]}"
            pdf_path = output_dir / f"{prefix}.pdf"
            json_path = output_dir / f"{prefix}.json"
            csv_path = output_dir / f"{prefix}.csv"

            # 1. Write JSON
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(summary_data, f, indent=2)

            # 2. Write CSV
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Call ID", "External ID", "Status", "Duration (s)", "Language", "Created At"])
                for c in calls:
                    writer.writerow([
                        str(c.id),
                        c.external_id or "",
                        c.status,
                        f"{c.duration:.1f}" if c.duration else "",
                        c.language or "en",
                        c.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    ])

            # 3. Write PDF
            cls._render_batch_pdf(
                output_path=pdf_path,
                company=company,
                batch=batch,
                summary=summary_data,
                calls=calls,
            )

            pdf_bytes = pdf_path.read_bytes() if pdf_path.exists() else None

            updated_report = ReportRepository.update_report_completed(
                db=db,
                report_id=report.id,
                file_path_pdf=str(pdf_path),
                file_path_json=str(json_path),
                file_path_csv=str(csv_path),
                summary_data=summary_data,
                pdf_data=pdf_bytes,
            )
            return updated_report or report

        except Exception as exc:
            logger.exception("Failed to generate batch analytics report %s: %s", report.id, exc)
            ReportRepository.update_report_failed(db, report.id, str(exc))
            raise

    # --------------------------------------------------------------------------
    # PDF Renderers using ReportLab
    # --------------------------------------------------------------------------

    @classmethod
    def _render_call_pdf(
        cls,
        output_path: Path,
        company: Company,
        call: Call,
        summary: dict[str, Any],
        turns: list[Any],
        risk: EscalationRisk | None,
    ) -> None:
        """Render a styled PDF report for an individual call."""
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#1E1B4B"),
            spaceAfter=4,
        )
        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#6B7280"),
            spaceAfter=15,
        )
        section_style = ParagraphStyle(
            "DocSection",
            parent=styles["Heading2"],
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#4338CA"),
            spaceBefore=12,
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "DocBody",
            parent=styles["Normal"],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#1F2937"),
        )
        bold_label = ParagraphStyle(
            "DocLabel",
            parent=body_style,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#374151"),
        )

        story = []

        # Header Banner
        story.append(Paragraph("AI CALL ANALYTICS — INTELLIGENCE REPORT", title_style))
        story.append(
            Paragraph(
                f"Workspace: <b>{company.name}</b> &nbsp;|&nbsp; Generated on: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
                subtitle_style,
            )
        )
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#6D5AE6"), spaceAfter=15))

        # Metadata Summary Grid
        meta_data = [
            [
                Paragraph("<b>Call ID:</b>", body_style),
                Paragraph(str(call.id)[:12] + "...", body_style),
                Paragraph("<b>External Ref:</b>", body_style),
                Paragraph(call.external_id or "N/A", body_style),
            ],
            [
                Paragraph("<b>Status:</b>", body_style),
                Paragraph(call.status, body_style),
                Paragraph("<b>Duration:</b>", body_style),
                Paragraph(_format_seconds(call.duration), body_style),
            ],
            [
                Paragraph("<b>Language:</b>", body_style),
                Paragraph((call.language or "en").upper(), body_style),
                Paragraph("<b>Recorded At:</b>", body_style),
                Paragraph(call.created_at.strftime("%Y-%m-%d %H:%M"), body_style),
            ],
            [
                Paragraph("<b>Dominant Sentiment:</b>", body_style),
                Paragraph(str(summary.get("dominant_sentiment", "N/A")), body_style),
                Paragraph("<b>Primary Intent:</b>", body_style),
                Paragraph(str(summary.get("primary_intent", "N/A")), body_style),
            ],
        ]
        meta_table = Table(meta_data, colWidths=[1.4 * inch, 1.8 * inch, 1.4 * inch, 2.4 * inch])
        meta_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F9FAFB")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ])
        )
        story.append(meta_table)
        story.append(Spacer(1, 15))

        # Escalation Risk Section
        story.append(Paragraph("Escalation Risk Evaluation", section_style))
        if risk:
            risk_color = "#DC2626" if risk.risk_score >= 70 else ("#D97706" if risk.risk_score >= 40 else "#059669")
            risk_data = [
                [
                    Paragraph("<b>Risk Score:</b>", body_style),
                    Paragraph(f"<font color='{risk_color}'><b>{risk.risk_score:.1f} / 100</b> ({risk.risk_level})</font>", body_style),
                    Paragraph("<b>Escalation Probability:</b>", body_style),
                    Paragraph(f"{risk.risk_probability * 100:.1f}%", body_style),
                ],
                [
                    Paragraph("<b>Explanation:</b>", body_style),
                    Paragraph(risk.explanation or "No high-risk triggers detected.", body_style),
                    "",
                    "",
                ],
            ]
            risk_table = Table(risk_data, colWidths=[1.4 * inch, 1.8 * inch, 1.4 * inch, 2.4 * inch])
            risk_table.setStyle(
                TableStyle([
                    ("SPAN", (1, 1), (3, 1)),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFBEB")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#FDE68A")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#FEF3C7")),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ])
            )
            story.append(risk_table)
        else:
            story.append(Paragraph("Risk analysis has not been processed for this call.", body_style))

        story.append(Spacer(1, 15))

        # Transcript & Turn-by-Turn Section
        story.append(Paragraph("Conversation Transcript & Turn-by-Turn Analysis", section_style))
        if turns:
            turns_rows = [
                [
                    Paragraph("<b>#</b>", bold_label),
                    Paragraph("<b>Speaker</b>", bold_label),
                    Paragraph("<b>Time</b>", bold_label),
                    Paragraph("<b>Utterance Text</b>", bold_label),
                    Paragraph("<b>Sentiment</b>", bold_label),
                ]
            ]
            for idx, t in enumerate(turns[:30], 1):  # Limit first 30 turns in PDF summary
                s_lbl = t.sentiment.get("label", "") if t.sentiment and isinstance(t.sentiment, dict) else "-"
                turns_rows.append([
                    Paragraph(str(idx), body_style),
                    Paragraph(t.speaker_id, body_style),
                    Paragraph(f"{t.start_time:.1f}s", body_style),
                    Paragraph(t.text, body_style),
                    Paragraph(s_lbl, body_style),
                ])

            turns_table = Table(turns_rows, colWidths=[0.3 * inch, 1.1 * inch, 0.7 * inch, 4.0 * inch, 0.9 * inch])
            turns_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4338CA")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ])
            )
            story.append(turns_table)
            if len(turns) > 30:
                story.append(Spacer(1, 6))
                story.append(Paragraph(f"<i>... and {len(turns) - 30} additional turns (see full CSV export for complete transcript).</i>", body_style))
        else:
            story.append(Paragraph("No transcribed turns available.", body_style))

        doc.build(story)

    @classmethod
    def _render_company_pdf(
        cls,
        output_path: Path,
        company: Company,
        summary: dict[str, Any],
        calls: list[Call],
    ) -> None:
        """Render a styled PDF executive report for company analytics."""
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#1E1B4B"),
            spaceAfter=4,
        )
        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#6B7280"),
            spaceAfter=15,
        )
        section_style = ParagraphStyle(
            "DocSection",
            parent=styles["Heading2"],
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#4338CA"),
            spaceBefore=12,
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "DocBody",
            parent=styles["Normal"],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#1F2937"),
        )
        bold_label = ParagraphStyle(
            "DocLabel",
            parent=body_style,
            fontName="Helvetica-Bold",
            textColor=colors.white,
        )

        story = []

        # Header
        story.append(Paragraph("EXECUTIVE CALL ANALYTICS REPORT", title_style))
        period_str = ""
        if summary.get("date_from") or summary.get("date_to"):
            period_str = f"Period: {summary.get('date_from', 'Start')} to {summary.get('date_to', 'Present')} &nbsp;|&nbsp; "
        story.append(
            Paragraph(
                f"Workspace: <b>{company.name}</b> &nbsp;|&nbsp; {period_str}Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
                subtitle_style,
            )
        )
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#6D5AE6"), spaceAfter=15))

        # KPI Metrics Table
        kpi_data = [
            [
                Paragraph("<b>Total Calls</b>", body_style),
                Paragraph(str(summary["total_calls"]), body_style),
                Paragraph("<b>Completed Calls</b>", body_style),
                Paragraph(str(summary["completed_count"]), body_style),
            ],
            [
                Paragraph("<b>Active Processing</b>", body_style),
                Paragraph(str(summary["processing_count"]), body_style),
                Paragraph("<b>Failed Ingestion</b>", body_style),
                Paragraph(str(summary["failed_count"]), body_style),
            ],
            [
                Paragraph("<b>Average Duration</b>", body_style),
                Paragraph(_format_seconds(summary["average_duration_seconds"]), body_style),
                Paragraph("<b>Avg Risk Score</b>", body_style),
                Paragraph(f"{summary['average_risk_score']:.1f} / 100", body_style),
            ],
        ]
        kpi_table = Table(kpi_data, colWidths=[1.5 * inch, 1.7 * inch, 1.5 * inch, 2.3 * inch])
        kpi_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F3F4F6")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ])
        )
        story.append(kpi_table)
        story.append(Spacer(1, 15))

        # Risk Classification Overview
        story.append(Paragraph("Escalation Risk Distribution", section_style))
        risk_dist = summary.get("risk_distribution", {})
        risk_table_data = [
            [
                Paragraph("<b>Risk Tier</b>", body_style),
                Paragraph("<b>Low Risk</b>", body_style),
                Paragraph("<b>Medium Risk</b>", body_style),
                Paragraph("<b>High Risk</b>", body_style),
                Paragraph("<b>Critical Risk</b>", body_style),
            ],
            [
                Paragraph("<b>Volume</b>", body_style),
                Paragraph(str(risk_dist.get("LOW", 0)), body_style),
                Paragraph(str(risk_dist.get("MEDIUM", 0)), body_style),
                Paragraph(str(risk_dist.get("HIGH", 0)), body_style),
                Paragraph(str(risk_dist.get("CRITICAL", 0)), body_style),
            ],
        ]
        r_table = Table(risk_table_data, colWidths=[1.4 * inch, 1.4 * inch, 1.4 * inch, 1.4 * inch, 1.4 * inch])
        r_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E0E7FF")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#C7D2FE")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E0E7FF")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ])
        )
        story.append(r_table)
        story.append(Spacer(1, 15))

        # Recent Call Inventory Table
        story.append(Paragraph(f"Call Inventory Log (Recent {min(len(calls), 25)} of {len(calls)} Calls)", section_style))
        if calls:
            inv_rows = [
                [
                    Paragraph("<b>Call ID</b>", bold_label),
                    Paragraph("<b>External Ref</b>", bold_label),
                    Paragraph("<b>Status</b>", bold_label),
                    Paragraph("<b>Duration</b>", bold_label),
                    Paragraph("<b>Created Date</b>", bold_label),
                ]
            ]
            for c in calls[:25]:
                inv_rows.append([
                    Paragraph(str(c.id)[:10] + "...", body_style),
                    Paragraph(c.external_id or "-", body_style),
                    Paragraph(c.status, body_style),
                    Paragraph(_format_seconds(c.duration), body_style),
                    Paragraph(c.created_at.strftime("%Y-%m-%d %H:%M"), body_style),
                ])

            inv_table = Table(inv_rows, colWidths=[1.5 * inch, 1.5 * inch, 1.2 * inch, 1.0 * inch, 1.8 * inch])
            inv_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4338CA")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ])
            )
            story.append(inv_table)
        else:
            story.append(Paragraph("No calls found for this company.", body_style))

        doc.build(story)

    @classmethod
    def _render_batch_pdf(
        cls,
        output_path: Path,
        company: Company,
        batch: Any,
        summary: dict[str, Any],
        calls: list[Call],
    ) -> None:
        """Render a styled PDF report for a batch upload."""
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#1E1B4B"),
            spaceAfter=4,
        )
        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#6B7280"),
            spaceAfter=15,
        )
        section_style = ParagraphStyle(
            "DocSection",
            parent=styles["Heading2"],
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#4338CA"),
            spaceBefore=12,
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "DocBody",
            parent=styles["Normal"],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#1F2937"),
        )
        bold_label = ParagraphStyle(
            "DocLabel",
            parent=body_style,
            fontName="Helvetica-Bold",
            textColor=colors.white,
        )

        story = []

        # Header
        story.append(Paragraph(f"BATCH ANALYTICS REPORT — {batch.display_name}", title_style))
        story.append(
            Paragraph(
                f"Workspace: <b>{company.name}</b> &nbsp;|&nbsp; File: <b>{batch.original_filename}</b> &nbsp;|&nbsp; Status: <b>{batch.status}</b> &nbsp;|&nbsp; Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
                subtitle_style,
            )
        )
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#6D5AE6"), spaceAfter=15))

        # KPI Metrics Table
        kpi_data = [
            [
                Paragraph("<b>Total Batch Calls</b>", body_style),
                Paragraph(str(summary["total_calls"]), body_style),
                Paragraph("<b>Completed Calls</b>", body_style),
                Paragraph(str(summary["completed_count"]), body_style),
            ],
            [
                Paragraph("<b>Processing / Queued</b>", body_style),
                Paragraph(str(summary["processing_count"] + summary.get("uploaded_count", 0)), body_style),
                Paragraph("<b>Failed Ingestion</b>", body_style),
                Paragraph(str(summary["failed_count"]), body_style),
            ],
            [
                Paragraph("<b>Average Duration</b>", body_style),
                Paragraph(_format_seconds(summary["average_duration_seconds"]), body_style),
                Paragraph("<b>Avg Risk Score</b>", body_style),
                Paragraph(f"{summary['average_risk_score']:.1f} / 100", body_style),
            ],
        ]
        kpi_table = Table(kpi_data, colWidths=[1.5 * inch, 1.7 * inch, 1.5 * inch, 2.3 * inch])
        kpi_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F3F4F6")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ])
        )
        story.append(kpi_table)
        story.append(Spacer(1, 15))

        # Risk Classification Overview
        story.append(Paragraph("Escalation Risk Distribution", section_style))
        risk_dist = summary.get("risk_distribution", {})
        risk_table_data = [
            [
                Paragraph("<b>Risk Tier</b>", body_style),
                Paragraph("<b>Low Risk</b>", body_style),
                Paragraph("<b>Medium Risk</b>", body_style),
                Paragraph("<b>High Risk</b>", body_style),
                Paragraph("<b>Critical Risk</b>", body_style),
            ],
            [
                Paragraph("<b>Volume</b>", body_style),
                Paragraph(str(risk_dist.get("LOW", 0)), body_style),
                Paragraph(str(risk_dist.get("MEDIUM", 0)), body_style),
                Paragraph(str(risk_dist.get("HIGH", 0)), body_style),
                Paragraph(str(risk_dist.get("CRITICAL", 0)), body_style),
            ],
        ]
        r_table = Table(risk_table_data, colWidths=[1.4 * inch, 1.4 * inch, 1.4 * inch, 1.4 * inch, 1.4 * inch])
        r_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E0E7FF")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#C7D2FE")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E0E7FF")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ])
        )
        story.append(r_table)
        story.append(Spacer(1, 15))

        # Call Inventory Table
        story.append(Paragraph(f"Batch Call Inventory ({len(calls)} Calls)", section_style))
        if calls:
            inv_rows = [
                [
                    Paragraph("<b>Call ID</b>", bold_label),
                    Paragraph("<b>External Ref / Audio</b>", bold_label),
                    Paragraph("<b>Status</b>", bold_label),
                    Paragraph("<b>Duration</b>", bold_label),
                    Paragraph("<b>Created Date</b>", bold_label),
                ]
            ]
            for c in calls[:100]:
                inv_rows.append([
                    Paragraph(str(c.id)[:10] + "...", body_style),
                    Paragraph(c.external_id or "-", body_style),
                    Paragraph(c.status, body_style),
                    Paragraph(_format_seconds(c.duration), body_style),
                    Paragraph(c.created_at.strftime("%Y-%m-%d %H:%M"), body_style),
                ])

            inv_table = Table(inv_rows, colWidths=[1.5 * inch, 1.7 * inch, 1.0 * inch, 1.0 * inch, 1.8 * inch])
            inv_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4338CA")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ])
            )
            story.append(inv_table)
        else:
            story.append(Paragraph("No calls found in this batch.", body_style))

        doc.build(story)

    @classmethod
    def get_report_download_artifact(
        cls,
        db: Session,
        report_id: uuid.UUID,
        company_id: uuid.UUID | None = None,
        file_format: str = "pdf",
    ) -> tuple[Path, str, str]:
        """
        Validate report ownership and return (file_path, content_type, safe_filename).
        Strictly enforces tenant isolation: report MUST belong to company_id if provided.
        """
        report = ReportRepository.get_by_id(db, report_id, company_id=company_id)
        if not report:
            raise AppException("REPORT_NOT_FOUND", f"Report '{report_id}' was not found.", 404)

        if report.status != ReportStatus.COMPLETED.value:
            raise AppException(
                "REPORT_NOT_READY",
                f"Report '{report_id}' status is '{report.status}'. Download is only available once COMPLETED.",
                400,
            )

        fmt = file_format.lower().strip()
        safe_base = _sanitize_filename(report.title)

        if fmt == "pdf":
            if not report.file_path_pdf or not os.path.exists(report.file_path_pdf):
                if report.pdf_data:
                    base_dir = Path("data") / "reports" / f"company_{report.company_id}"
                    base_dir.mkdir(parents=True, exist_ok=True)
                    restored_path = base_dir / f"restored_{str(report.id)[:8]}_{safe_base}.pdf"
                    restored_path.write_bytes(report.pdf_data)
                    return restored_path, "application/pdf", f"{safe_base}.pdf"
                raise AppException("FILE_NOT_FOUND", "PDF report file not found on disk or database.", 404)
            return Path(report.file_path_pdf), "application/pdf", f"{safe_base}.pdf"

        elif fmt == "json":
            if not report.file_path_json or not os.path.exists(report.file_path_json):
                raise AppException("FILE_NOT_FOUND", "JSON report file not found on disk.", 404)
            return Path(report.file_path_json), "application/json", f"{safe_base}.json"

        elif fmt in ("csv", "excel"):
            if not report.file_path_csv or not os.path.exists(report.file_path_csv):
                raise AppException("FILE_NOT_FOUND", "CSV report file not found on disk.", 404)
            return Path(report.file_path_csv), "text/csv; charset=utf-8", f"{safe_base}.csv"

        else:
            raise AppException("UNSUPPORTED_FORMAT", f"Report format '{file_format}' is not supported. Choose pdf, json, or csv.", 400)
