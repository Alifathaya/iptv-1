package com.fotojelas.pro.ui.viewmodel

import android.app.Application
import android.graphics.Bitmap
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.fotojelas.pro.FotoJelasApplication
import com.fotojelas.pro.domain.model.EnhancePreset
import com.fotojelas.pro.domain.model.EnhanceRequest
import com.fotojelas.pro.domain.model.HistoryItem
import com.fotojelas.pro.util.ImageLoader
import com.fotojelas.pro.util.MediaStoreSaver
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class HomeUiState(
    val history: List<HistoryItem> = emptyList(),
    val isLoading: Boolean = false,
)

class HomeViewModel(application: Application) : AndroidViewModel(application) {
    private val fotoApp = application as FotoJelasApplication
    private val _state = MutableStateFlow(HomeUiState())
    val state: StateFlow<HomeUiState> = _state.asStateFlow()

    fun loadHistory() {
        viewModelScope.launch {
            _state.update { it.copy(isLoading = true) }
            val items = fotoApp.historyRepository.refresh()
            _state.update { it.copy(history = items, isLoading = false) }
        }
    }

    fun deleteHistory(id: Long) {
        viewModelScope.launch {
            fotoApp.historyRepository.delete(id)
            loadHistory()
        }
    }
}

data class EnhanceUiState(
    val original: Bitmap? = null,
    val enhanced: Bitmap? = null,
    val preset: EnhancePreset = EnhancePreset.NATURAL,
    val comparePosition: Float = 0.5f,
    val isProcessing: Boolean = false,
    val progress: Float = 0f,
    val progressMessage: String = "",
    val sharpness: Float = 0.45f,
    val cloudApiUrl: String = "",
    val cloudApiKey: String = "",
    val error: String? = null,
    val saveMessage: String? = null,
)

class EnhanceViewModel(application: Application) : AndroidViewModel(application) {
    private val fotoApp = application as FotoJelasApplication
    private val _state = MutableStateFlow(
        EnhanceUiState(
            cloudApiUrl = fotoApp.preferences.cloudApiUrl,
            cloudApiKey = fotoApp.preferences.cloudApiKey,
        )
    )
    val state: StateFlow<EnhanceUiState> = _state.asStateFlow()

    private var originalPath: String? = null

    fun setOriginal(bitmap: Bitmap) {
        viewModelScope.launch {
            val path = ImageLoader.saveToCache(fotoApp, bitmap, "original")
            originalPath = path
            _state.update {
                it.copy(
                    original = bitmap,
                    enhanced = null,
                    error = null,
                    saveMessage = null,
                )
            }
        }
    }

    fun setPreset(preset: EnhancePreset) {
        _state.update { it.copy(preset = preset) }
    }

    fun setComparePosition(value: Float) {
        _state.update { it.copy(comparePosition = value.coerceIn(0f, 1f)) }
    }

    fun setSharpness(value: Float) {
        _state.update { it.copy(sharpness = value.coerceIn(0f, 1f)) }
    }

    fun setCloudSettings(url: String, key: String) {
        fotoApp.preferences.cloudApiUrl = url
        fotoApp.preferences.cloudApiKey = key
        _state.update { it.copy(cloudApiUrl = url, cloudApiKey = key) }
    }

    fun enhance() {
        val original = _state.value.original ?: return
        viewModelScope.launch {
            _state.update {
                it.copy(
                    isProcessing = true,
                    progress = 0f,
                    progressMessage = "Memulai AI…",
                    error = null,
                )
            }
            try {
                val request = EnhanceRequest(
                    preset = _state.value.preset,
                    sharpness = _state.value.sharpness,
                    cloudApiUrl = _state.value.cloudApiUrl,
                    cloudApiKey = _state.value.cloudApiKey,
                )
                val result = fotoApp.enhanceOrchestrator.enhance(
                    original,
                    request,
                    { pct, msg ->
                        _state.update {
                            it.copy(progress = pct, progressMessage = msg)
                        }
                    },
                )
                val enhancedPath = ImageLoader.saveToCache(fotoApp, result.bitmap, "enhanced")
                val origPath = originalPath ?: ImageLoader.saveToCache(fotoApp, original, "original")

                fotoApp.historyRepository.add(
                    HistoryItem(
                        originalPath = origPath,
                        enhancedPath = enhancedPath,
                        preset = _state.value.preset.name,
                        createdAt = System.currentTimeMillis(),
                        width = result.outputWidth,
                        height = result.outputHeight,
                    )
                )

                _state.update {
                    it.copy(
                        enhanced = result.bitmap,
                        isProcessing = false,
                        progress = 1f,
                        progressMessage = "Selesai!",
                    )
                }
            } catch (e: Exception) {
                _state.update {
                    it.copy(
                        isProcessing = false,
                        error = e.message ?: "Gagal memproses gambar",
                    )
                }
            }
        }
    }

    fun saveToGallery() {
        val enhanced = _state.value.enhanced ?: return
        viewModelScope.launch {
            try {
                MediaStoreSaver.saveToGallery(
                    fotoApp,
                    enhanced,
                    "fotojelas_${System.currentTimeMillis()}.png",
                )
                _state.update { it.copy(saveMessage = "Disimpan ke Pictures/FotoJelasPro") }
            } catch (e: Exception) {
                _state.update { it.copy(error = e.message ?: "Gagal menyimpan") }
            }
        }
    }

    fun clearMessages() {
        _state.update { it.copy(error = null, saveMessage = null) }
    }
}
