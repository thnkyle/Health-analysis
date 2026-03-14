package com.healthanalysis.data

import com.healthanalysis.data.models.AuthRequest
import com.healthanalysis.data.models.AuthResponse
import com.healthanalysis.data.models.SyncRequest
import com.healthanalysis.data.models.SyncResponse
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.POST

interface HealthApi {
    @POST("api/v1/sync")
    suspend fun syncRecords(@Body request: SyncRequest): SyncResponse

    @POST("api/v1/auth/register")
    suspend fun register(@Body request: AuthRequest): Map<String, Any>

    @POST("api/v1/auth/login")
    suspend fun login(@Body request: AuthRequest): AuthResponse
}

class SyncService(baseUrl: String) {
    private var authToken: String? = null

    private val authInterceptor = Interceptor { chain ->
        val builder = chain.request().newBuilder()
        authToken?.let { builder.addHeader("Authorization", "Bearer $it") }
        chain.proceed(builder.build())
    }

    private val client = OkHttpClient.Builder()
        .addInterceptor(authInterceptor)
        .build()

    private val api: HealthApi = Retrofit.Builder()
        .baseUrl(baseUrl)
        .client(client)
        .addConverterFactory(GsonConverterFactory.create())
        .build()
        .create(HealthApi::class.java)

    fun setToken(token: String) {
        authToken = token
    }

    suspend fun register(username: String, password: String): Result<Unit> {
        return try {
            api.register(AuthRequest(username, password))
            Result.success(Unit)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun login(username: String, password: String): Result<String> {
        return try {
            val response = api.login(AuthRequest(username, password))
            authToken = response.accessToken
            Result.success(response.accessToken)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

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
