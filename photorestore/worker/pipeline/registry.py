"""Registry mode -> pipeline. Ultra menyusul (difusi/GPU Phase 4-6)."""
from .basic import BasicEnhance
from .color import ColorEnhance
from .denoise import Denoise
from .face_detect import FaceDetect
from .face_restore import FaceRestore
from .quality import QualityAnalysis
from .upscale import Upscale

PIPELINES = {
    "basic": [QualityAnalysis(), Denoise(), BasicEnhance(), Upscale()],
    "hd": [QualityAnalysis(), Denoise(), BasicEnhance(), FaceDetect(),
           FaceRestore(), Upscale(), ColorEnhance()],
}
