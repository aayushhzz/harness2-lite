import json
from pathlib import Path
from typing import Dict, Optional

from h2.llmjson import call_json
from h2.paths import Config
from h2.prompts import CONTRAST_SCHEMA, CONTRAST_SYSTEM, contrast_prompt
from h2.signals import default_cites, signal_deltas
from h2.trace import StepIndex, read_steps

LABELS = ("mitigated", "unchanged", "regressed")


def _validate(data: dict) -> None:
    if data.get("label") not in LABELS:
        raise ValueError("label must be one of mitigated, unchanged, regressed")
    for key in ("targeted_deficiency", "observed_change"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise ValueError(f"{key} must be a non-empty string")
    cs = data.get("cited_steps")
    if not isinstance(cs, list) or not all(isinstance(x, str) for x in cs):
        raise ValueError("cited_steps must be an array of strings")


def contrast(task, proposals: Dict[str, Optional[object]], ref_rec, cand_recs: Dict[str, object], backend,
             cfg: Config, run_dir: Path, tokens_out: Optional[dict] = None) -> dict:
    run_dir = Path(run_dir)
    index = StepIndex(run_dir)
    ref_steps = read_steps(run_dir / "reference.jsonl")
    out: Dict[str, dict] = {}
    for scope in ("invariant", "domain"):
        prop = proposals.get(scope)
        rec = cand_recs.get(scope)
        if prop is None or rec is None:
            out[scope] = {"skipped": "no_valid_proposal"}
            continue
        deltas = signal_deltas(ref_rec.signals, rec.signals)
        sig_block = {"reference": ref_rec.signals, "candidate": rec.signals, "deltas": deltas}
        prompt = contrast_prompt(task, scope, prop, ref_steps, rec.steps, sig_block, ref_rec.diff, rec.diff)
        data, tokens = call_json(backend, "contrast", CONTRAST_SYSTEM, prompt, CONTRAST_SCHEMA, _validate,
                                 run_dir / "prompts", retries=1, log_name=f"contrast_{scope}")
        if tokens_out is not None:
            tokens_out[scope] = tokens_out.get(scope, 0) + tokens
        default = default_cites(ref_steps, rec.steps)
        entry = {"scope": scope, "signals_reference": ref_rec.signals,
                 "signals_candidate": rec.signals, "signal_deltas": deltas}
        if data is None:
            entry.update({"targeted_deficiency": prop.targeted_deficiency,
                          "observed_change": "contrast call failed", "label": "unchanged",
                          "regression": False, "cited_steps": default, "cites_source": "code_fallback",
                          "llm_failed": True})
        else:
            label = data["label"]
            cited = index.filter_valid(data.get("cited_steps", []))
            source = "llm"
            if not cited:
                cited = default
                source = "code_fallback"
            entry.update({"targeted_deficiency": data["targeted_deficiency"].strip(),
                          "observed_change": data["observed_change"].strip(),
                          "label": label, "regression": label == "regressed",
                          "cited_steps": cited, "cites_source": source})
        out[scope] = entry
    result = {"task": task.id, "candidates": out}
    (run_dir / "contrast.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
