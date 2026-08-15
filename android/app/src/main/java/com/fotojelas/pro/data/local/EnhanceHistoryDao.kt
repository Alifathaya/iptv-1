package com.fotojelas.pro.data.local

import androidx.room.Dao
import androidx.room.Entity
import androidx.room.Insert
import androidx.room.PrimaryKey
import androidx.room.Query

@Entity(tableName = "enhance_history")
data class EnhanceHistoryEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val originalPath: String,
    val enhancedPath: String,
    val preset: String,
    val createdAt: Long,
    val width: Int,
    val height: Int,
)

@Dao
interface EnhanceHistoryDao {
    @Query("SELECT * FROM enhance_history ORDER BY createdAt DESC")
    suspend fun getAll(): List<EnhanceHistoryEntity>

    @Insert
    suspend fun insert(item: EnhanceHistoryEntity): Long

    @Query("DELETE FROM enhance_history WHERE id = :id")
    suspend fun delete(id: Long)
}
