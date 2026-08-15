/**
 * Image enhancement filters — usable in main thread and Web Worker.
 */

export function clamp(v, min, max) {
  return Math.max(min, Math.min(max, v));
}

export function cloneImageData(imageData) {
  return new ImageData(
    new Uint8ClampedArray(imageData.data),
    imageData.width,
    imageData.height
  );
}

export function scaleImageData(imageData, newW, newH) {
  const srcCanvas = new OffscreenCanvas(imageData.width, imageData.height);
  srcCanvas.getContext('2d').putImageData(imageData, 0, 0);

  const destCanvas = new OffscreenCanvas(newW, newH);
  const ctx = destCanvas.getContext('2d');
  const upscaling = newW > imageData.width || newH > imageData.height;
  ctx.imageSmoothingEnabled = !upscaling;
  ctx.imageSmoothingQuality = 'high';
  ctx.drawImage(srcCanvas, 0, 0, newW, newH);

  return ctx.getImageData(0, 0, newW, newH);
}

export function fitMaxDimension(imageData, maxDim) {
  const maxSide = Math.max(imageData.width, imageData.height);
  if (maxSide <= maxDim) return imageData;
  const scale = maxDim / maxSide;
  const w = Math.round(imageData.width * scale);
  const h = Math.round(imageData.height * scale);
  return scaleImageData(imageData, w, h);
}

/** Laplacian convolution sharpen — no blur, only adds edge detail */
export function applyConvolutionSharpen(imageData, amount) {
  if (amount <= 0) return imageData;

  const { width, height, data } = imageData;
  const copy = new Uint8ClampedArray(data);
  const s = amount * 0.1;

  for (let y = 1; y < height - 1; y++) {
    for (let x = 1; x < width - 1; x++) {
      const i = (y * width + x) * 4;
      for (let c = 0; c < 3; c++) {
        const center = copy[i + c];
        const val =
          center * (1 + 4 * s)
          - copy[i - 4 + c] * s
          - copy[i + 4 + c] * s
          - copy[i - width * 4 + c] * s
          - copy[i + width * 4 + c] * s;
        data[i + c] = clamp(Math.round(val), 0, 255);
      }
    }
  }

  return imageData;
}

/** Separable box blur — only used inside unsharp mask (radius 1–2) */
export function boxBlur(imageData, radius) {
  if (radius <= 0) return cloneImageData(imageData);

  const { width, height, data } = imageData;
  const out = new Uint8ClampedArray(data.length);
  const tmp = new Float32Array(data.length);
  const r = Math.max(1, Math.round(radius));

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      let sumR = 0, sumG = 0, sumB = 0, count = 0;
      for (let dx = -r; dx <= r; dx++) {
        const nx = clamp(x + dx, 0, width - 1);
        const i = (y * width + nx) * 4;
        sumR += data[i];
        sumG += data[i + 1];
        sumB += data[i + 2];
        count++;
      }
      const o = (y * width + x) * 4;
      tmp[o] = sumR / count;
      tmp[o + 1] = sumG / count;
      tmp[o + 2] = sumB / count;
      tmp[o + 3] = data[o + 3];
    }
  }

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      let sumR = 0, sumG = 0, sumB = 0, count = 0;
      for (let dy = -r; dy <= r; dy++) {
        const ny = clamp(y + dy, 0, height - 1);
        const i = (ny * width + x) * 4;
        sumR += tmp[i];
        sumG += tmp[i + 1];
        sumB += tmp[i + 2];
        count++;
      }
      const o = (y * width + x) * 4;
      out[o] = sumR / count;
      out[o + 1] = sumG / count;
      out[o + 2] = sumB / count;
      out[o + 3] = data[o + 3];
    }
  }

  return new ImageData(out, width, height);
}

export function applyBrightnessContrast(imageData, brightness, contrast) {
  const data = imageData.data;
  const b = brightness * 2.55;
  const factor = (259 * (contrast + 255)) / (255 * (259 - contrast));

  for (let i = 0; i < data.length; i += 4) {
    let r = data[i] + b;
    let g = data[i + 1] + b;
    let bl = data[i + 2] + b;

    r = factor * (r - 128) + 128;
    g = factor * (g - 128) + 128;
    bl = factor * (bl - 128) + 128;

    data[i] = clamp(Math.round(r), 0, 255);
    data[i + 1] = clamp(Math.round(g), 0, 255);
    data[i + 2] = clamp(Math.round(bl), 0, 255);
  }

  return imageData;
}

export function applyUnsharpMask(imageData, amount, radius) {
  if (amount <= 0) return imageData;

  const blurred = boxBlur(imageData, radius);
  const src = imageData.data;
  const blur = blurred.data;
  const strength = amount / 35;

  for (let i = 0; i < src.length; i += 4) {
    const dr = src[i] - blur[i];
    const dg = src[i + 1] - blur[i + 1];
    const db = src[i + 2] - blur[i + 2];

    src[i] = clamp(Math.round(src[i] + dr * strength), 0, 255);
    src[i + 1] = clamp(Math.round(src[i + 1] + dg * strength), 0, 255);
    src[i + 2] = clamp(Math.round(src[i + 2] + db * strength), 0, 255);
  }

  return imageData;
}

/** High-pass detail boost — sharpens without smearing */
export function applyHighPassSharpen(imageData, amount) {
  if (amount <= 0) return imageData;

  const blurred = boxBlur(imageData, 5);
  const src = imageData.data;
  const blur = blurred.data;
  const strength = amount / 100 * 1.8;

  for (let i = 0; i < src.length; i += 4) {
    for (let c = 0; c < 3; c++) {
      const detail = src[i + c] - blur[i + c];
      src[i + c] = clamp(Math.round(src[i + c] + detail * strength), 0, 255);
    }
  }

  return imageData;
}

export function applyMultiPassSharpen(imageData, amount) {
  if (amount <= 0) return imageData;
  let data = imageData;
  data = applyUnsharpMask(data, amount, 1);
  data = applyUnsharpMask(data, amount * 0.75, 2);
  if (amount > 55) {
    data = applyHighPassSharpen(data, amount * 0.9);
  }
  return data;
}

export function applyClarity(imageData, amount) {
  if (amount <= 0) return imageData;

  const blurred = boxBlur(imageData, 8);
  const src = imageData.data;
  const blur = blurred.data;
  const strength = amount / 100;

  for (let i = 0; i < src.length; i += 4) {
    const lum = 0.299 * src[i] + 0.587 * src[i + 1] + 0.114 * src[i + 2];
    const lumBlur = 0.299 * blur[i] + 0.587 * blur[i + 1] + 0.114 * blur[i + 2];
    const midWeight = 1 - Math.abs(lum - 128) / 128;
    const delta = (lum - lumBlur) * strength * midWeight * 2.2;

    src[i] = clamp(Math.round(src[i] + delta), 0, 255);
    src[i + 1] = clamp(Math.round(src[i + 1] + delta), 0, 255);
    src[i + 2] = clamp(Math.round(src[i + 2] + delta), 0, 255);
  }

  return imageData;
}

export function applyDenoise(imageData, amount) {
  if (amount <= 0) return imageData;

  const blurred = boxBlur(imageData, 1);
  const src = imageData.data;
  const blur = blurred.data;
  const threshold = 6 + amount * 0.2;
  const blend = (amount / 100) * 0.45;

  for (let i = 0; i < src.length; i += 4) {
    const dr = src[i] - blur[i];
    const dg = src[i + 1] - blur[i + 1];
    const db = src[i + 2] - blur[i + 2];
    const diff = Math.sqrt(dr * dr + dg * dg + db * db);

    if (diff < threshold) {
      src[i] = Math.round(src[i] * (1 - blend) + blur[i] * blend);
      src[i + 1] = Math.round(src[i + 1] * (1 - blend) + blur[i + 1] * blend);
      src[i + 2] = Math.round(src[i + 2] * (1 - blend) + blur[i + 2] * blend);
    }
  }

  return imageData;
}

export function applyLocalContrast(imageData, amount) {
  if (amount <= 0) return imageData;

  const blurred = boxBlur(imageData, 12);
  const src = imageData.data;
  const blur = blurred.data;
  const strength = amount / 80;

  for (let i = 0; i < src.length; i += 4) {
    for (let c = 0; c < 3; c++) {
      const detail = src[i + c] - blur[i + c];
      src[i + c] = clamp(Math.round(src[i + c] + detail * strength), 0, 255);
    }
  }

  return imageData;
}

export function upscaleImageData(imageData, percent) {
  if (percent <= 0) return imageData;

  const scale = 1 + percent / 100;
  const newW = Math.round(imageData.width * scale);
  const newH = Math.round(imageData.height * scale);
  return scaleImageData(imageData, newW, newH);
}

function createGaussianKernel(size, sigma) {
  const kernel = new Float32Array(size * size);
  const cx = (size - 1) / 2;
  let sum = 0;

  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const dx = x - cx;
      const dy = y - cx;
      const v = Math.exp(-(dx * dx + dy * dy) / (2 * sigma * sigma));
      kernel[y * size + x] = v;
      sum += v;
    }
  }

  for (let i = 0; i < kernel.length; i++) kernel[i] /= sum;
  return kernel;
}

function convolveChannel(src, width, height, kernel, ksize) {
  const half = Math.floor(ksize / 2);
  const out = new Float32Array(src.length);

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      let sum = 0;
      for (let ky = 0; ky < ksize; ky++) {
        for (let kx = 0; kx < ksize; kx++) {
          const px = clamp(x + kx - half, 0, width - 1);
          const py = clamp(y + ky - half, 0, height - 1);
          sum += src[py * width + px] * kernel[ky * ksize + kx];
        }
      }
      out[y * width + x] = sum;
    }
  }

  return out;
}

function extractChannel(imageData, channel) {
  const { width, height, data } = imageData;
  const ch = new Float32Array(width * height);
  for (let i = 0, p = 0; i < data.length; i += 4, p++) {
    ch[p] = data[i + channel];
  }
  return ch;
}

function writeChannel(imageData, channel, src) {
  const data = imageData.data;
  for (let i = 0, p = 0; i < data.length; i += 4, p++) {
    data[i + channel] = clamp(Math.round(src[p]), 0, 255);
  }
}

/** Richardson-Lucy — only mild strength; high values cause muddy blur */
export function applyRichardsonLucy(imageData, strength) {
  if (strength <= 0) return imageData;

  const capped = Math.min(strength, 45);
  const { width, height } = imageData;
  const sigma = 0.6 + capped * 0.03;
  const ksize = clamp(Math.ceil(sigma * 4) | 1, 3, 9);
  const iterations = Math.round(2 + capped * 0.08);
  const kernel = createGaussianKernel(ksize, sigma);

  const data = cloneImageData(imageData);

  for (let ch = 0; ch < 3; ch++) {
    const original = extractChannel(data, ch);
    let estimate = new Float32Array(original);

    for (let iter = 0; iter < iterations; iter++) {
      const convEst = convolveChannel(estimate, width, height, kernel, ksize);
      const ratio = new Float32Array(estimate.length);

      for (let i = 0; i < ratio.length; i++) {
        ratio[i] = original[i] / Math.max(convEst[i], 1e-4);
      }

      const correction = convolveChannel(ratio, width, height, kernel, ksize);

      for (let i = 0; i < estimate.length; i++) {
        estimate[i] = clamp(estimate[i] * correction[i], 0, 255);
      }
    }

    writeChannel(data, ch, estimate);
  }

  return data;
}

export function applyEdgeEnhance(imageData, amount) {
  if (amount <= 0) return imageData;

  const { width, height, data } = imageData;
  const strength = amount / 100;
  const copy = new Uint8ClampedArray(data);

  for (let y = 1; y < height - 1; y++) {
    for (let x = 1; x < width - 1; x++) {
      const i = (y * width + x) * 4;
      for (let c = 0; c < 3; c++) {
        const lap =
          -copy[i - width * 4 + c] - copy[i - 4 + c] + 4 * copy[i + c]
          - copy[i + 4 + c] - copy[i + width * 4 + c];
        data[i + c] = clamp(Math.round(copy[i + c] + lap * strength * 0.35), 0, 255);
      }
    }
  }

  return imageData;
}

function applySettingsPipeline(data, settings, { deblur = 0, multiSharpen = false, localContrast = false } = {}) {
  const contrastVal = settings.contrast * 1.4;
  const brightnessVal = settings.brightness;

  if (brightnessVal !== 0 || contrastVal !== 0) {
    data = applyBrightnessContrast(data, brightnessVal, contrastVal);
  }

  if (settings.clarity > 0) {
    data = applyClarity(data, settings.clarity);
  }

  if (localContrast) {
    data = applyLocalContrast(data, settings.clarity + settings.sharpness * 0.6);
  }

  data = applyHighPassSharpen(data, settings.sharpness * 0.7);

  if (settings.sharpness > 0) {
    if (multiSharpen) {
      data = applyMultiPassSharpen(data, settings.sharpness);
    } else {
      data = applyUnsharpMask(data, settings.sharpness, 1);
      if (settings.sharpness > 40) {
        data = applyUnsharpMask(data, settings.sharpness * 0.5, 2);
      }
    }
  }

  if (deblur > 0) {
    data = applyRichardsonLucy(data, deblur);
  }

  if (settings.denoise > 35) {
    data = applyDenoise(data, settings.denoise);
  }

  if (settings.upscale > 0) {
    data = upscaleImageData(data, settings.upscale);
  }

  return data;
}

/** Sharpen-first pipeline — ZERO blur/denoise/deblur (safe default) */
export function processClarify(imageData, settings) {
  let data = cloneImageData(imageData);

  const sharp = Math.max(settings.sharpness, 55);
  const clarityExtra = settings.clarity * 0.5;
  const contrastVal = 12 + settings.contrast * 1.4;

  data = applyConvolutionSharpen(data, sharp + clarityExtra);
  data = applyUnsharpMask(data, sharp * 1.4, 1);
  data = applyConvolutionSharpen(data, (sharp + clarityExtra) * 0.45);
  data = applyUnsharpMask(data, sharp * 0.8, 1);
  data = applyBrightnessContrast(data, settings.brightness, contrastVal);

  return data;
}

export function processFast(imageData, settings) {
  return processClarify(imageData, settings);
}

export function processPro(imageData, settings) {
  let data = processClarify(imageData, settings);

  if (settings.deblur > 50) {
    data = applyRichardsonLucy(data, Math.min(settings.deblur, 35));
    data = applyConvolutionSharpen(data, settings.sharpness * 0.6);
    data = applyUnsharpMask(data, settings.sharpness, 1);
  }

  return data;
}

export function processExtremePre(imageData, settings) {
  let data = fitMaxDimension(imageData, 1280);

  data = applyConvolutionSharpen(data, Math.min(settings.sharpness, 45));
  data = applyUnsharpMask(data, settings.sharpness * 0.8, 1);

  if (settings.deblur > 55) {
    data = applyRichardsonLucy(data, Math.min(settings.deblur, 35));
    data = applyConvolutionSharpen(data, settings.sharpness * 0.5);
  }

  return data;
}

export function processPostPolish(imageData, settings) {
  let data = cloneImageData(imageData);
  const sharp = Math.max(settings.sharpness, 50);

  data = applyConvolutionSharpen(data, sharp);
  data = applyUnsharpMask(data, sharp * 1.3, 1);
  data = applyConvolutionSharpen(data, sharp * 0.35);
  data = applyBrightnessContrast(data, settings.brightness, 10 + settings.contrast * 1.2);

  return data;
}
