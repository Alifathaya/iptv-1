package com.fotojelas.pro

import android.Manifest
import android.graphics.Bitmap
import android.net.Uri
import android.os.Build
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.google.accompanist.permissions.ExperimentalPermissionsApi
import com.google.accompanist.permissions.isGranted
import com.google.accompanist.permissions.rememberMultiplePermissionsState
import com.google.accompanist.permissions.rememberPermissionState
import com.fotojelas.pro.ui.camera.CameraScreen
import com.fotojelas.pro.ui.screens.EnhanceScreen
import com.fotojelas.pro.ui.screens.HomeScreen
import com.fotojelas.pro.ui.theme.FotoJelasTheme
import com.fotojelas.pro.ui.viewmodel.EnhanceViewModel
import com.fotojelas.pro.ui.viewmodel.HomeViewModel
import com.fotojelas.pro.util.ImageLoader
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {

    @OptIn(ExperimentalPermissionsApi::class)
    override fun onCreate(savedInstanceState: android.os.Bundle?) {
        super.onCreate(savedInstanceState)

        setContent {
            FotoJelasTheme {
                val navController = rememberNavController()
                val homeViewModel: HomeViewModel = viewModel()
                val enhanceViewModel: EnhanceViewModel = viewModel()
                val scope = rememberCoroutineScope()
                var showCamera by remember { mutableStateOf(false) }
                var showPermissionRationale by remember { mutableStateOf(false) }

                val mediaPermission = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                    Manifest.permission.READ_MEDIA_IMAGES
                } else {
                    Manifest.permission.READ_EXTERNAL_STORAGE
                }

                val storagePermissions = rememberMultiplePermissionsState(
                    listOf(mediaPermission),
                )
                val cameraPermission = rememberPermissionState(Manifest.permission.CAMERA)

                val galleryLauncher = rememberLauncherForActivityResult(
                    ActivityResultContracts.PickVisualMedia(),
                ) { uri: Uri? ->
                    uri?.let { u ->
                        scope.launch {
                            try {
                                val bitmap = ImageLoader.decodeFromUri(this@MainActivity, u)
                                enhanceViewModel.setOriginal(bitmap)
                            } catch (_: Exception) {
                            }
                        }
                    }
                }

                LaunchedEffect(Unit) {
                    homeViewModel.loadHistory()
                }

                if (showPermissionRationale) {
                    AlertDialog(
                        onDismissRequest = { showPermissionRationale = false },
                        title = { Text("Izin diperlukan") },
                        text = {
                            Text(
                                "Foto Jelas Pro membutuhkan akses kamera dan galeri untuk memuat, memproses, dan menyimpan foto Anda.",
                            )
                        },
                        confirmButton = {
                            TextButton(onClick = { showPermissionRationale = false }) {
                                Text("Mengerti")
                            }
                        },
                    )
                }

                if (showCamera) {
                    if (!cameraPermission.status.isGranted) {
                        LaunchedEffect(Unit) {
                            cameraPermission.launchPermissionRequest()
                        }
                    }
                    if (cameraPermission.status.isGranted) {
                        CameraScreen(
                            onPhotoCaptured = { bitmap ->
                                enhanceViewModel.setOriginal(bitmap)
                                showCamera = false
                            },
                            onClose = { showCamera = false },
                        )
                    }
                } else {
                    NavHost(
                        navController = navController,
                        startDestination = "home",
                        modifier = Modifier.fillMaxSize(),
                    ) {
                        composable("home") {
                            HomeScreen(
                                viewModel = homeViewModel,
                                onNewEnhance = {
                                    navController.navigate("enhance")
                                },
                            )
                        }
                        composable("enhance") {
                            EnhanceScreen(
                                viewModel = enhanceViewModel,
                                onBack = {
                                    homeViewModel.loadHistory()
                                    navController.popBackStack()
                                },
                                onOpenCamera = {
                                    if (!cameraPermission.status.isGranted) {
                                        showPermissionRationale = true
                                        cameraPermission.launchPermissionRequest()
                                    } else {
                                        showCamera = true
                                    }
                                },
                                onOpenGallery = {
                                    if (!storagePermissions.allPermissionsGranted) {
                                        showPermissionRationale = true
                                        storagePermissions.launchMultiplePermissionRequest()
                                    } else {
                                        galleryLauncher.launch(
                                            PickVisualMediaRequest(
                                                ActivityResultContracts.PickVisualMedia.ImageOnly,
                                            ),
                                        )
                                    }
                                },
                            )
                        }
                    }
                }
            }
        }
    }
}
