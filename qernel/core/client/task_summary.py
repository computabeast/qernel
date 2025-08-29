"""Helpers for summarizing tasks and extracting analysis details."""

from collections.abc import Mapping
from typing import Any, Optional


def _get_pipeline(analysis: Optional[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    if not analysis:
        return []
    pipeline = (analysis or {}).get("pipeline")
    return pipeline if isinstance(pipeline, list) else []


def _matches_any_keyword(step: Mapping[str, Any], keywords: list[str]) -> bool:
    name = str((step or {}).get("name", "")).lower()
    return any(kw in name for kw in keywords)


def _slice_known_output_fields(out: Mapping[str, Any]) -> dict[str, Any]:
    fields = ["counts", "shots", "mitigated_value", "raw_value", "metrics"]
    result: dict[str, Any] = {}
    if "summary" in out:
        result["summary"] = out["summary"]
    for key in fields:
        if key in out:
            result[key] = out[key]
    return result


def _collect_step_details_from_output(out: Mapping[str, Any]) -> dict[str, Any]:
    details: dict[str, Any] = {}
    step_sum = out.get("summary")
    if isinstance(step_sum, Mapping):
        keys = ["t_count", "qubit_count", "depth", "op_counts", "mitigated_value"]
        details.update({key: step_sum[key] for key in keys if key in step_sum})
    for key in ["mitigated_value", "raw_value"]:
        val = out.get(key)
        if val is not None:
            details[key] = val
    counts = out.get("counts")
    if isinstance(counts, Mapping):
        details["counts"] = counts
    shots = out.get("shots")
    if shots is not None:
        details["shots"] = shots
    return details


def extract_task_specs_from_doc(doc: Optional[str]) -> list[dict[str, Any]]:
    """Return a list of task specs inferred from a class docstring."""
    if not doc:
        return []
    text = (doc or "").lower()
    specs: list[dict[str, Any]] = []
    if ("resource" in text) or ("estimate" in text):
        specs.append(
            {
                "id": "resource_estimation",
                "title": "Resource Estimation",
                "keywords": [
                    "resource.qualtran",
                    "qualtran",
                    "resource",
                    "estimate",
                    "resource_estimation",
                ],
            }
        )
    if ("mitiq" in text) or ("zne" in text) or ("error mitigation" in text):
        specs.append(
            {
                "id": "error_mitigation_zne",
                "title": "Error Mitigation (Mitiq ZNE)",
                "keywords": [
                    "mitigation.mitiq.zne",
                    "mitiq",
                    "zne",
                    "mitigation",
                ],
            }
        )
    if (
        ("simulate" in text)
        or ("simulation" in text)
        or ("histogram" in text)
        or ("shots" in text)
    ):
        specs.append(
            {
                "id": "simulation_histogram",
                "title": "Simulation (Histogram)",
                "keywords": [
                    "execute.simulator",
                    "simulator",
                    "execute",
                    "histogram",
                    "counts",
                    "shots",
                ],
            }
        )
    return specs


def task_payload_slice(
    analysis: Optional[Mapping[str, Any]], keywords: list[str]
) -> dict[str, Any]:
    """Return a compact payload slice for pipeline steps matching keywords."""
    pipeline = _get_pipeline(analysis)
    matched = [step for step in pipeline if _matches_any_keyword(step, keywords)]
    if not matched:
        return {}
    if len(matched) > 1:
        return {"pipeline": matched}
    step = matched[0]
    out = (step or {}).get("output") or {}
    if isinstance(out, Mapping):
        sliced = _slice_known_output_fields(out)
        return {"pipeline": [step], "output": sliced or out}
    return {"pipeline": [step]}


def task_details_from_analysis(
    analysis: Optional[Mapping[str, Any]], keywords: list[str]
) -> dict[str, Any]:
    """Return compact details for steps that match provided keywords."""
    details: dict[str, Any] = {}
    for step in _get_pipeline(analysis):
        if _matches_any_keyword(step, keywords):
            out = (step or {}).get("output") or {}
            if isinstance(out, Mapping):
                details.update(_collect_step_details_from_output(out))
    return details


def summarize_tasks(
    build_doc: Optional[str], analysis: Optional[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    """Summarize likely tasks using docstring hints and pipeline analysis."""
    specs = extract_task_specs_from_doc(build_doc)
    summary: list[dict[str, Any]] = []
    for spec in specs:
        details = task_details_from_analysis(analysis, spec["keywords"])
        payload = task_payload_slice(analysis, spec["keywords"])
        status = "success" if details or payload else "info"
        summary.append(
            {
                "id": spec["id"],
                "title": spec["title"],
                "status": status,
                "details": details,
                "json": payload,
            }
        )
    return summary
