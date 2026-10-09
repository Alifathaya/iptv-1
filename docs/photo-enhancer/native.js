/* API native via window.Capacitor global (disuntik WebView) — tanpa impor npm.
   Di web biasa: stub aman, semua fungsi fallback ke perilaku web. */

function cap() {
  if (typeof window !== 'undefined' && window.Capacitor) return window.Capacitor;
  return null;
}

function stub() {
  return {
    isNativePlatform: () => false,
    Plugins: {},
  };
}

export function isNativeApp() {
  try {
    return (cap() || stub()).isNativePlatform();
  } catch {
    return false;
  }
}

function needPlugins() {
  const c = cap();
  if (!c || !c.Plugins) throw new Error('bukan aplikasi native');
  return c.Plugins;
}

async function initNative() {
  if (!isNativeApp()) return;
  try {
    const P = needPlugins();
    if (P.StatusBar) {
      await P.StatusBar.setStyle({ style: 'DARK' });
      await P.StatusBar.setBackgroundColor({ color: '#070b14' });
    }
    if (P.SplashScreen) await P.SplashScreen.hide();
  } catch {
    /* optional */
  }
}

export { initNative };

export async function pickNativePhoto() {
  const P = needPlugins();
  if (!P.Camera) throw new Error('plugin Kamera tidak ada');
  const res = await P.Camera.pickImages({ limit: 1, quality: 90 });
  const photo = res.photos && res.photos[0];
  if (!photo) throw new Error('batal');
  const url = photo.webPath || photo.path;
  const r = await fetch(url);
  const blob = await r.blob();
  return new File([blob], 'foto.jpg', { type: blob.type || 'image/jpeg' });
}

export async function saveAndShareImage(dataUrl) {
  const P = needPlugins();
  const base64 = dataUrl.split(',')[1];
  const fileName = `foto-jelas-pro-${Date.now()}.png`;
  await P.Filesystem.writeFile({ path: fileName, data: base64, directory: 'CACHE' });
  const { uri } = await P.Filesystem.getUri({ path: fileName, directory: 'CACHE' });
  await P.Share.share({ title: 'Foto Jelas Pro', text: 'Foto yang sudah diperjelas', url: uri, dialogTitle: 'Bagikan foto' });
  return uri;
}

export async function saveToDocuments(dataUrl) {
  const P = needPlugins();
  const base64 = dataUrl.split(',')[1];
  const fileName = `foto-jelas-pro-${Date.now()}.png`;
  await P.Filesystem.writeFile({ path: fileName, data: base64, directory: 'DOCUMENTS' });
  return fileName;
}
