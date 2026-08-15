import {
  processFast,
  processPro,
  processExtremePre,
  processPostPolish,
} from './filters.js';

function report(pct, message) {
  self.postMessage({ type: 'progress', pct, message });
}

self.onmessage = (e) => {
  const { task, imageData, settings, mode } = e.data;

  if (task === 'process') {
    try {
      report(10, 'Menganalisis piksel…');

      let result;
      if (mode === 'fast') {
        report(40, 'Mempertajam detail…');
        result = processFast(imageData, settings);
      } else if (mode === 'pro') {
        report(25, 'Deblur Richardson-Lucy…');
        result = processPro(imageData, settings);
        report(80, 'Finishing Pro…');
      } else if (mode === 'pre-extreme') {
        report(20, 'Deblur ekstrem (iteratif)…');
        result = processExtremePre(imageData, settings);
        report(70, 'Pra-pemrosesan AI selesai…');
      } else if (mode === 'post-polish') {
        report(50, 'Polish akhir…');
        result = processPostPolish(imageData, settings);
        report(90, 'Merapikan hasil…');
      } else {
        result = processFast(imageData, settings);
      }

      report(100, 'Selesai!');
      self.postMessage(
        { type: 'done', imageData: result, mode },
        [result.data.buffer]
      );
    } catch (err) {
      self.postMessage({ type: 'error', message: err.message || 'Processing failed' });
    }
  }
};
