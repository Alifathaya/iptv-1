package com.fotojelas.pro

import android.app.Application
import com.fotojelas.pro.data.repository.HistoryRepository
import com.fotojelas.pro.ml.EnhanceOrchestrator
import com.fotojelas.pro.util.AppPreferences

class FotoJelasApplication : Application() {
    lateinit var historyRepository: HistoryRepository
    lateinit var enhanceOrchestrator: EnhanceOrchestrator
    lateinit var preferences: AppPreferences

    override fun onCreate() {
        super.onCreate()
        historyRepository = HistoryRepository(this)
        enhanceOrchestrator = EnhanceOrchestrator(this)
        preferences = AppPreferences(this)
    }
}
