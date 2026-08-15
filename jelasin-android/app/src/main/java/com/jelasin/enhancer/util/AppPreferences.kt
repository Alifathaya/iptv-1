package com.jelasin.enhancer.util

import android.content.Context

class AppPreferences(context: Context) {
    private val prefs = context.getSharedPreferences("jelasin_prefs", Context.MODE_PRIVATE)

    var cloudApiUrl: String
        get() = prefs.getString("cloud_api_url", "") ?: ""
        set(value) = prefs.edit().putString("cloud_api_url", value).apply()

    var cloudApiKey: String
        get() = prefs.getString("cloud_api_key", "") ?: ""
        set(value) = prefs.edit().putString("cloud_api_key", value).apply()
}
