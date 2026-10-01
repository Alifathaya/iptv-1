"""Registry mode -> pipeline. HD/Ultra menyusul (butuh model wajah Phase 3)."""
from .basic import BasicEnhance
from .denoise import Denoise
from .quality import QualityAnalysis
from .upscale import Upscale

PIPELINES = {
    "basic": [QualityAnalysis(), Denoise(), BasicEnhance(), Upscale()],
}
