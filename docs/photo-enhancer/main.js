import { initNative, isNativeApp, saveAndShareImage, saveToDocuments } from './native.js';
import { initApp } from './app.js';

await initNative();
initApp();

if ('serviceWorker' in navigator && !isNativeApp()) {
  navigator.serviceWorker.register('./sw.js').catch(() => {});
}
