package com.fotojelas.pro.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.PhotoLibrary
import androidx.compose.material.icons.filled.Save
import androidx.compose.material.icons.filled.AutoFixHigh
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Slider
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.dp
import com.fotojelas.pro.domain.model.EnhancePreset
import com.fotojelas.pro.ui.components.BeforeAfterSlider
import com.fotojelas.pro.ui.components.ScanningLineOverlay
import com.fotojelas.pro.ui.viewmodel.EnhanceViewModel

@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
fun EnhanceScreen(
    viewModel: EnhanceViewModel,
    onBack: () -> Unit,
    onOpenCamera: () -> Unit,
    onOpenGallery: () -> Unit,
) {
    val state by viewModel.state.collectAsState()
    val snackbar = remember { SnackbarHostState() }

    LaunchedEffect(state.error, state.saveMessage) {
        state.error?.let { snackbar.showSnackbar(it) }
        state.saveMessage?.let { snackbar.showSnackbar(it) }
        viewModel.clearMessages()
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbar) },
        topBar = {
            TopAppBar(
                title = { Text("Perjelas Foto") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Kembali")
                    }
                },
            )
        },
    ) { padding ->
        Column(
            Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            Box(
                Modifier
                    .fillMaxWidth()
                    .height(320.dp),
            ) {
                when {
                    state.original != null && state.enhanced != null -> {
                        BeforeAfterSlider(
                            position = state.comparePosition,
                            onPositionChange = viewModel::setComparePosition,
                            modifier = Modifier.fillMaxSize(),
                            before = {
                                Image(
                                    bitmap = state.original!!.asImageBitmap(),
                                    contentDescription = "Sebelum",
                                    modifier = Modifier.fillMaxSize(),
                                    contentScale = ContentScale.Fit,
                                )
                            },
                            after = {
                                Image(
                                    bitmap = state.enhanced!!.asImageBitmap(),
                                    contentDescription = "Sesudah",
                                    modifier = Modifier.fillMaxSize(),
                                    contentScale = ContentScale.Fit,
                                )
                            },
                        )
                    }
                    state.original != null -> {
                        Image(
                            bitmap = state.original!!.asImageBitmap(),
                            contentDescription = "Original",
                            modifier = Modifier.fillMaxSize(),
                            contentScale = ContentScale.Fit,
                        )
                    }
                    else -> {
                        Text(
                            "Pilih foto dari galeri atau kamera",
                            modifier = Modifier.align(Alignment.Center),
                        )
                    }
                }

                if (state.isProcessing) {
                    ScanningLineOverlay(
                        message = state.progressMessage.ifBlank {
                            "AI sedang menganalisis dan merekonstruksi piksel…"
                        },
                        modifier = Modifier.fillMaxSize(),
                    )
                    CircularProgressIndicator(
                        modifier = Modifier.align(Alignment.Center),
                    )
                }
            }

            FlowRow(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                EnhancePreset.entries.forEach { preset ->
                    FilterChip(
                        selected = state.preset == preset,
                        onClick = { viewModel.setPreset(preset) },
                        label = { Text(preset.label) },
                    )
                }
            }

            Text("Ketajaman konvolusi: ${(state.sharpness * 100).toInt()}%")
            Slider(
                value = state.sharpness,
                onValueChange = viewModel::setSharpness,
                valueRange = 0f..1f,
            )

            OutlinedTextField(
                value = state.cloudApiUrl,
                onValueChange = { viewModel.setCloudSettings(it, state.cloudApiKey) },
                label = { Text("URL Cloud GPU (opsional)") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )
            OutlinedTextField(
                value = state.cloudApiKey,
                onValueChange = { viewModel.setCloudSettings(state.cloudApiUrl, it) },
                label = { Text("API Key Cloud") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
            )

            Button(
                onClick = onOpenGallery,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Icon(Icons.Default.PhotoLibrary, contentDescription = null)
                Text("Pilih Galeri", modifier = Modifier.padding(start = 8.dp))
            }

            Button(
                onClick = onOpenCamera,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Icon(Icons.Default.CameraAlt, contentDescription = null)
                Text("Kamera", modifier = Modifier.padding(start = 8.dp))
            }

            Button(
                onClick = viewModel::enhance,
                enabled = state.original != null && !state.isProcessing,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Icon(Icons.Default.AutoFixHigh, contentDescription = null)
                Text(
                    if (state.isProcessing) "Memproses ${(state.progress * 100).toInt()}%"
                    else "✦ Perjelas dengan AI",
                    modifier = Modifier.padding(start = 8.dp),
                )
            }

            Button(
                onClick = viewModel::saveToGallery,
                enabled = state.enhanced != null && !state.isProcessing,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Icon(Icons.Default.Save, contentDescription = null)
                Text("Simpan ke Galeri", modifier = Modifier.padding(start = 8.dp))
            }
        }
    }
}
