"""Classification Agent — benign/malicious + type prediction.

Phase 0: transparent heuristic scorer over agent evidence (type votes from
static imports, severity-weighted findings, triage entropy). Weeks 7–8 swap in
an XGBoost model trained on EMBER behind the exact same ``classify()`` signature
(see docs/PLAN.md §6.3) — the orchestrator and interfaces won't change.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import numpy as np

from nullify.core.agents.base import BaseAgent
from nullify.core.ember_features import ember_feature_vector_from_bytes
from nullify.core.events import EventBus
from nullify.core.models import (
    AgentResult,
    AgentStatus,
    FileTarget,
    Finding,
    ScanMode,
    Severity,
    Target,
    Verdict,
)

try:
    import xgboost as xgb
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False


SEVERITY_WEIGHTS: dict[Severity, float] = {
    Severity.INFO: 0.0,
    Severity.LOW: 1.0,
    Severity.MEDIUM: 2.5,
    Severity.HIGH: 5.0,
    Severity.CRITICAL: 9.0,
}

# Votes needed from static import hints to strongly suggest a type.
STRONG_TYPE_VOTES = 2
MALICIOUS_SCORE_THRESHOLD = 6.0
SUSPICIOUS_SCORE_THRESHOLD = 2.0

# Severity ranking used to fuse model and evidence verdicts.
_VERDICT_RANK: dict[Verdict, int] = {
    Verdict.BENIGN: 0,
    Verdict.SUSPICIOUS: 1,
    Verdict.MALICIOUS: 2,
}

# Inference reads at most the first 20 MiB of the target (EMBER convention).
_MAX_INFERENCE_BYTES = 20_971_520


def _model_probability(model: Any, target_path: str | Path | None) -> float | None:
    """Target bytes -> EMBER feature vector -> model P(malicious).

    Returns None when the target cannot be read or the model cannot predict,
    so callers fall back to evidence-only scoring instead of crashing.
    """
    if target_path is None:
        return None
    try:
        with open(target_path, "rb") as fh:
            features = ember_feature_vector_from_bytes(fh.read(_MAX_INFERENCE_BYTES))
        proba = model.predict_proba(np.asarray([features], dtype=np.float32))
        return float(proba[0, 1])
    except Exception:  # noqa: BLE001 — any failure degrades to evidence-only verdict
        return None


def classify(evidence: dict[str, Any], model: Any = None, target_path: str | Path | None = None) -> dict[str, Any]:
    """Pure function: evidence dict → verdict/type/confidence + reasons.

    Kept side-effect-free so it is trivially testable and so the weeks 7–8
    XGBoost swap only replaces this function's internals.
    """
    reasons: list[str] = []

    # 1. Optional model path: EMBER features -> P(malicious). Fused with the
    #    evidence score below — the more severe verdict wins, and the model
    #    can escalate (never downgrade) the evidence-only verdict.
    prob: float | None = None
    if model is not None and target_path is not None:
        prob = _model_probability(model, target_path)

    # 2. Evidence score (always computed — also drives skip logic upstream).
    score = 0.0

    reputation = evidence.get("reputation") or {}
    if reputation.get("known_malicious"):
        score += 10.0
        reasons.append("hash has known-bad reputation")

    type_votes: dict[str, int] = dict(evidence.get("type_votes") or {})
    best_type, best_votes = ("", 0)
    for mal_type, votes in type_votes.items():
        if votes > best_votes:
            best_type, best_votes = mal_type, votes
    if best_votes:
        score += min(best_votes * 1.5, 6.0)
        reasons.append(f"static imports suggest {best_type} ({best_votes} API hits)")

    for f in evidence.get("findings", []):
        try:
            sev = Severity(f.get("severity", "info"))
        except ValueError:
            sev = Severity.INFO
        score += SEVERITY_WEIGHTS.get(sev, 0.0)

    if evidence.get("packed"):
        score += 2.0
        reasons.append("binary appears packed (high entropy)")

    verdict = Verdict.BENIGN
    if score >= MALICIOUS_SCORE_THRESHOLD:
        verdict = Verdict.MALICIOUS
    elif score >= SUSPICIOUS_SCORE_THRESHOLD:
        verdict = Verdict.SUSPICIOUS

    # 3. Fusion: the model's verdict is combined with the evidence verdict —
    #    the more severe of the two wins, so the model can escalate a
    #    suspicious-looking binary but never wash out real static evidence.
    engine = "heuristic-phase0"
    if prob is not None:
        model_verdict = (
            Verdict.MALICIOUS
            if prob >= 0.85
            else Verdict.SUSPICIOUS
            if prob >= 0.4
            else Verdict.BENIGN
        )
        reasons.append(f"XGBoost EMBER model probability: {prob:.4f}")
        if _VERDICT_RANK[model_verdict] > _VERDICT_RANK[verdict]:
            verdict = model_verdict
            reasons.append("model verdict overrides evidence-only score")
        engine = "xgboost-ember"
        if score == 0.0:
            # Pure-model verdicts keep the calibrated probability as the score
            # so the reported number stays comparable across engines.
            score = prob

    malware_type = "unknown"
    if verdict is Verdict.BENIGN:
        malware_type = "benign"
    elif best_votes >= STRONG_TYPE_VOTES and best_type:
        malware_type = best_type

    confidence = min(score / 15.0, 0.99) if verdict is not Verdict.BENIGN else max(
        0.5, min(0.9, 0.9 - score / 10.0)
    )
    if malware_type not in ("unknown", "benign"):
        confidence = max(confidence, min(0.6 + 0.1 * best_votes, 0.95))

    return {
        "verdict": verdict,
        "malware_type": malware_type,
        "confidence": round(confidence, 3),
        "score": round(score, 2),
        "reasons": reasons,
        "engine": engine
    }


class ClassificationAgent(BaseAgent):
    """Folds evidence from prior agents into a verdict + malware type."""

    name = "Classifier"
    
    def __init__(self, bus: EventBus | None = None, config: dict[str, Any] | None = None,
                 model_path: str | Path | None = None):
        super().__init__(bus=bus, config=config)
        self.model = None
        
        if model_path is None:
            model_path = os.environ.get("NULLIFY_MODEL_PATH", "models/malware_xgb.json")
            
        self.model_path = Path(model_path)
        
        if XGB_AVAILABLE and self.model_path.exists():
            try:
                self.model = xgb.XGBClassifier()
                self.model.load_model(self.model_path)
            except Exception:  # noqa: BLE001
                self.model = None

    def analyze(self, target: Target, mode: ScanMode) -> AgentResult:
        from nullify.core.models import AnalysisResult  # noqa: F401  (typing hook)

        evidence = self.config.get("evidence", {})
        # The EMBER model is a PE classifier — it only applies to file targets.
        # Log targets and other target kinds always go through evidence scoring.
        model_applies = self.model is not None and isinstance(target, FileTarget)
        if not evidence and not model_applies:
            return AgentResult(agent=self.name, status=AgentStatus.SKIPPED,
                               data={"reason": "no upstream evidence provided"})

        target_path = target.path if model_applies else None
        result = classify(evidence, model=self.model if model_applies else None,
                          target_path=target_path)
        
        title_prefix = "XGBoost score" if self.model else "Heuristic score"
        
        findings = [
            Finding(
                agent=self.name,
                title=f"{title_prefix} {result['score']}",
                detail="; ".join(result["reasons"]) or "no aggravating evidence",
                severity=_verdict_severity(result["verdict"]),
                metadata={"score": result["score"]},
            )
        ]

        return AgentResult(
            agent=self.name,
            status=AgentStatus.COMPLETED,
            findings=findings,
            data={
                "engine": result.get("engine", "heuristic-phase0"),
                "verdict": result["verdict"].value,
                "malware_type": result["malware_type"],
                "confidence": result["confidence"],
                "score": result["score"],
                "reasons": result["reasons"],
            },
        )


def _verdict_severity(verdict: Verdict) -> Severity:
    return {
        Verdict.MALICIOUS: Severity.CRITICAL,
        Verdict.SUSPICIOUS: Severity.MEDIUM,
        Verdict.BENIGN: Severity.INFO,
        Verdict.UNKNOWN: Severity.LOW,
    }[verdict]
