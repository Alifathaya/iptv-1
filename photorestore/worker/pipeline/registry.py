"""Registry mode -> pipeline. HD/Ultra menyusul (butuh model wajah Phase 3)."""
from .basic import BasicEnhance
from .quality import QualityAnalysis

PIPELINES = {
    "basic": [QualityAnalysis(), BasicEnhance()],
}
