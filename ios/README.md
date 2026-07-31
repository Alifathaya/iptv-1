# Kalkulator iOS

Aplikasi kalkulator native untuk iOS, dibangun dengan SwiftUI.

## Persyaratan

- macOS dengan Xcode 15 atau lebih baru
- iOS 16.0+
- iPhone atau iPad

## Cara Membuka Proyek

1. Clone repository ini
2. Buka `ios/Calculator.xcodeproj` di Xcode
3. Pilih simulator atau perangkat fisik
4. Tekan **Run** (⌘R)

## Fitur

- Operasi dasar: penjumlahan, pengurangan, perkalian, pembagian
- Tombol AC (hapus semua), ± (ubah tanda), % (persentase)
- Format angka lokal Indonesia
- Penanganan pembagian dengan nol
- Desain gelap yang responsif untuk iPhone dan iPad
- Dukungan SwiftUI Preview untuk pengembangan cepat

## Struktur Proyek

```
ios/
├── Calculator.xcodeproj/
└── Calculator/
    ├── CalculatorApp.swift      # Entry point aplikasi
    ├── ContentView.swift        # Tampilan utama kalkulator
    ├── CalculatorViewModel.swift # Logika perhitungan
    ├── CalculatorButton.swift   # Komponen tombol kustom
    └── Assets.xcassets/         # Icon dan warna
```

## Build untuk App Store

1. Buka proyek di Xcode
2. Pilih target **Calculator**
3. Ubah **Bundle Identifier** sesuai Apple Developer Account Anda
4. Pilih **Product → Archive**
5. Ikuti wizard untuk upload ke App Store Connect
