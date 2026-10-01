"""Registry mode -> pipeline. Generatif (OpenAI) menyusul Phase 6."""
from .basic import BasicEnhance
from .color import ColorEnhance
from .deblur import DeblurProcessor
from .denoise import Denoise
from .face_detect import FaceDetect
from .face_restore import FaceRestore
from .qc import QualityGate
from .quality import QualityAnalysis
from .upscale import Upscale

PIPELINES = {
    "basic": [QualityAnalysis(), Denoise(), BasicEnhance(), Upscale()],
    "hd": [QualityAnalysis(), Denoise(), DeblurProcessor(), BasicEnhance(),
           FaceDetect(), FaceRestore(), Upscale(), ColorEnhance(), QualityGate()],
    "ultra": [QualityAnalysis(), Denoise(), DeblurProcessor(), BasicEnhance(),
              FaceDetect(), FaceRestore(), Upscale(), ColorEnhance(), QualityGate()],
}