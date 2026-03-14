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

    fun getLastSyncTime(): Instant {
        val millis = prefs.getLong("last_sync", 0)
        return if (millis > 0) Instant.ofEpochMilli(millis) else Instant.now().minus(7, ChronoUnit.DAYS)
    }

    fun updateLastSyncTime() {
        prefs.edit().putLong("last_sync", Instant.now().toEpochMilli()).apply()
    }

    fun saveToken(token: String) {
        prefs.edit().putString("auth_token", token).apply()
    }

    fun getToken(): String? {
        return prefs.getString("auth_token", null)
    }

    fun saveUsername(username: String) {
        prefs.edit().putString("username", username).apply()
    }

    fun getUsername(): String? {
        return prefs.getString("username", null)
    }

    fun isLoggedIn(): Boolean = getToken() != null

    fun logout() {
        prefs.edit()
            .remove("auth_token")
            .remove("username")
            .apply()
    }

    suspend fun fetchNewRecords(): List<HealthDataRecord> {
        val since = getLastSyncTime()
        return healthConnectManager.readAllData(since)
    }
}
