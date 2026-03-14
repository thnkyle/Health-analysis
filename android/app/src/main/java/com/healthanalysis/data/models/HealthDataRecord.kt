package com.healthanalysis.data.models

import com.google.gson.annotations.SerializedName

data class HealthDataRecord(
    @SerializedName("data_type") val dataType: String,
    val value: Double,
    val unit: String,
    @SerializedName("recorded_at") val recordedAt: String,
    @SerializedName("metadata_json") val metadataJson: String = "{}"
)

data class SyncRequest(
    val records: List<HealthDataRecord>
)

data class SyncResponse(
    val inserted: Int,
    val message: String
)

data class AuthRequest(
    val username: String,
    val password: String
)

data class AuthResponse(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("token_type") val tokenType: String
)
