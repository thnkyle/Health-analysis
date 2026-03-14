package com.healthanalysis.data

import com.healthanalysis.data.models.SyncRequest
import com.healthanalysis.data.models.SyncResponse
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.POST

interface HealthApi {
    @POST("api/v1/sync")
    suspend fun syncRecords(@Body request: SyncRequest): SyncResponse
}

class SyncService(baseUrl: String) {
    private val api: HealthApi = Retrofit.Builder()
        .baseUrl(baseUrl)
        .addConverterFactory(GsonConverterFactory.create())
        .build()
        .create(HealthApi::class.java)

    suspend fun sync(repository: HealthDataRepository): Result<SyncResponse> {
        return try {
            val records = repository.fetchNewRecords()
            if (records.isEmpty()) {
                return Result.success(SyncResponse(inserted = 0, message = "No new records"))
            }
            val response = api.syncRecords(SyncRequest(records))
            repository.updateLastSyncTime()
            Result.success(response)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
