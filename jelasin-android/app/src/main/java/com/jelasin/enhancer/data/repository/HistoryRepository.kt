package com.jelasin.enhancer.data.repository

import android.content.Context
import com.jelasin.enhancer.data.local.AppDatabase
import com.jelasin.enhancer.data.local.EnhanceHistoryEntity
import com.jelasin.enhancer.domain.model.HistoryItem
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.flowOn
import kotlinx.coroutines.withContext

class HistoryRepository(private val context: Context) {
    private val dao = AppDatabase.get(context).historyDao()

    fun observeHistory(): Flow<List<HistoryItem>> = flow {
        emit(dao.getAll().map { it.toDomain() })
    }.flowOn(Dispatchers.IO)

    suspend fun refresh(): List<HistoryItem> = withContext(Dispatchers.IO) {
        dao.getAll().map { it.toDomain() }
    }

    suspend fun add(item: HistoryItem): Long = withContext(Dispatchers.IO) {
        dao.insert(
            EnhanceHistoryEntity(
                originalPath = item.originalPath,
                enhancedPath = item.enhancedPath,
                preset = item.preset,
                createdAt = item.createdAt,
                width = item.width,
                height = item.height,
            )
        )
    }

    suspend fun delete(id: Long) = withContext(Dispatchers.IO) {
        dao.delete(id)
    }

    private fun EnhanceHistoryEntity.toDomain() = HistoryItem(
        id = id,
        originalPath = originalPath,
        enhancedPath = enhancedPath,
        preset = preset,
        createdAt = createdAt,
        width = width,
        height = height,
    )
}
