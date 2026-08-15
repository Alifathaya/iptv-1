package com.jelasin.enhancer

import android.app.Application
import com.jelasin.enhancer.data.repository.HistoryRepository
import com.jelasin.enhancer.ml.EnhanceOrchestrator
import com.jelasin.enhancer.util.AppPreferences

class JelasinApplication : Application() {
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
