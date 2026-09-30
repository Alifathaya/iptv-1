import { Capacitor } from '@capacitor/core';

export function isNativeApp() {
  return Capacitor.isNativePlatform();
}

async function plugins() {
  const { Share } = await import('@capacitor/share');
  const { Filesystem, Directory } = await import('@capacitor/filesystem');
  const { StatusBar, Style } = await import('@capacitor/status-bar');
  const { SplashScreen } = await import('@capacitor/splash-screen');
  return { Share, Filesystem, Directory, StatusBar, Style, SplashScreen };
}

export async function initNative() {
  if (!isNativeApp()) return;

  try {
    const { StatusBar, Style, SplashScreen } = await plugins();
    await StatusBar.setStyle({ style: Style.Dark });
    await StatusBar.setBackgroundColor({ color: '#070b14' });
    await SplashScreen.hide();
  } catch {
    /* optional */
  }
}

export async function saveAndShareImage(dataUrl) {
  const { Share, Filesystem, Directory } = await plugins();
  const base64 = dataUrl.split(',')[1];
  const fileName = `foto-jelas-pro-${Date.now()}.png`;

  await Filesystem.writeFile({
    path: fileName,
    data: base64,
    directory: Directory.Cache,
  });

  const { uri } = await Filesystem.getUri({
    path: fileName,
    directory: Directory.Cache,
  });

  await Share.share({
    title: 'Foto Jelas Pro',
    text: 'Foto yang sudah diperjelas',
    url: uri,
    dialogTitle: 'Bagikan foto',
  });

  return uri;
}

export async function saveToDocuments(dataUrl) {
  const { Filesystem, Directory } = await plugins();
  const base64 = dataUrl.split(',')[1];
  const fileName = `foto-jelas-pro-${Date.now()}.png`;

  await Filesystem.writeFile({
    path: fileName,
    data: base64,
    directory: Directory.Documents,
  });

  return fileName;
}
