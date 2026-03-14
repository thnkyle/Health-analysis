package com.healthanalysis.data

import android.content.Context
import android.content.SharedPreferences
import com.healthanalysis.HealthConnectManager
import com.healthanalysis.data.models.HealthDataRecord
import java.time.Instant
import java.time.temporal.ChronoUnit

class HealthDataRepository(
    private val context: Context,
    private val healthConnectManager: HealthConnectManager
) {
    private val prefs: SharedPreferences =
        context.getSharedPreferences("health_sync", Context.MODE_PRIVATE)

    private val userId: String
        get() = prefs.getString("user_id", "default_user") ?: "default_user"

    fun getLastSyncTime(): Instant {
        val millis = prefs.getLong("last_sync", 0)
        return if (millis > 0) Instant.ofEpochMilli(millis) else Instant.now().minus(7, ChronoUnit.DAYS)
    }

    fun updateLastSyncTime() {
        prefs.edit().putLong("last_sync", Instant.now().toEpochMilli()).apply()
    }

    suspend fun fetchNewRecords(): List<HealthDataRecord> {
        val since = getLastSyncTime()
        return healthConnectManager.readAllData(since).map {
            it.copy(userId = userId)
        }
    }
}
