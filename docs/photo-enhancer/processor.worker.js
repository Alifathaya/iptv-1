/**
 * Web Worker — pemrosesan gambar di latar belakang (setara coroutine).
 * Konvolusi ketajaman 3×3 async agar UI tidak lag.
 */
import {
  processFastAsync,
  processProAsync,
  processExtremePre,
  processPostPolish,
} from './filters.js';

function report(jobId, pct, message) {
  self.postMessage({ jobId, type: 'progress', pct, message });
}

function toImageData(payload) {
  return new ImageData(
    new Uint8ClampedArray(payload.data),
    payload.width,
    payload.height
  );
}

function fromImageData(imageData) {
  return {
    width: imageData.width,
    height: imageData.height,
    data: imageData.data,
  };
}

self.onmessage = async (e) => {
  const { jobId, task, imageData, settings, mode } = e.data;

  if (task !== 'process') return;

  const input = toImageData(imageData);

  try {
    report(jobId, 5, 'Worker: memulai pemrosesan…');

    let result;

    if (mode === 'fast') {
      result = await processFastAsync(input, settings, (pct, msg) => report(jobId, pct, msg));
    } else if (mode === 'pro') {
      result = await processProAsync(input, settings, (pct, msg) => report(jobId, pct, msg));
    } else if (mode === 'pre-extreme') {
      report(jobId, 20, 'Deblur ekstrem (iteratif)…');
      result = processExtremePre(input, settings);
      report(jobId, 70, 'Pra-pemrosesan AI selesai…');
    } else if (mode === 'post-polish') {
      report(jobId, 50, 'Polish akhir…');
      result = processPostPolish(input, settings);
      report(jobId, 90, 'Merapikan hasil…');
    } else {
      result = await processFastAsync(input, settings, (pct, msg) => report(jobId, pct, msg));
    }

    report(jobId, 100, 'Selesai!');

    self.postMessage({
      jobId,
      type: 'done',
      imageData: fromImageData(result),
      mode,
    });
  } catch (err) {
    self.postMessage({
      jobId,
      type: 'error',
      message: err.message || 'Processing failed',
    });
  }
};
