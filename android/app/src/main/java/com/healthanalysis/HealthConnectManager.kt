package com.healthanalysis

import android.content.Context
import androidx.health.connect.client.HealthConnectClient
import androidx.health.connect.client.permission.HealthPermission
import androidx.health.connect.client.records.*
import androidx.health.connect.client.request.ReadRecordsRequest
import androidx.health.connect.client.time.TimeRangeFilter
import com.healthanalysis.data.models.HealthDataRecord
import java.time.Instant
import java.time.ZoneOffset

class HealthConnectManager(private val context: Context) {

    private val client by lazy { HealthConnectClient.getOrCreate(context) }

    val permissions = setOf(
        HealthPermission.getReadPermission(StepsRecord::class),
        HealthPermission.getReadPermission(DistanceRecord::class),
        HealthPermission.getReadPermission(TotalCaloriesBurnedRecord::class),
        HealthPermission.getReadPermission(ExerciseSessionRecord::class),
        HealthPermission.getReadPermission(HeartRateRecord::class),
        HealthPermission.getReadPermission(BloodPressureRecord::class),
        HealthPermission.getReadPermission(BodyTemperatureRecord::class),
        HealthPermission.getReadPermission(WeightRecord::class),
        HealthPermission.getReadPermission(SleepSessionRecord::class),
        HealthPermission.getReadPermission(NutritionRecord::class),
    )

    suspend fun hasAllPermissions(): Boolean {
        val granted = client.permissionController.getGrantedPermissions()
        return permissions.all { it in granted }
    }

    suspend fun readAllData(since: Instant): List<HealthDataRecord> {
        val timeRange = TimeRangeFilter.between(since, Instant.now())
        val records = mutableListOf<HealthDataRecord>()

        records.addAll(readSteps(timeRange))
        records.addAll(readDistance(timeRange))
        records.addAll(readCalories(timeRange))
        records.addAll(readHeartRate(timeRange))
        records.addAll(readBloodPressure(timeRange))
        records.addAll(readBodyTemperature(timeRange))
        records.addAll(readWeight(timeRange))
        records.addAll(readSleep(timeRange))

        return records
    }

    private suspend fun readSteps(timeRange: TimeRangeFilter): List<HealthDataRecord> {
        val response = client.readRecords(ReadRecordsRequest(StepsRecord::class, timeRange))
        return response.records.map {
            HealthDataRecord(
                dataType = "steps",
                value = it.count.toDouble(),
                unit = "count",
                recordedAt = it.endTime.atOffset(ZoneOffset.UTC).toString()
            )
        }
    }

    private suspend fun readDistance(timeRange: TimeRangeFilter): List<HealthDataRecord> {
        val response = client.readRecords(ReadRecordsRequest(DistanceRecord::class, timeRange))
        return response.records.map {
            HealthDataRecord(
                dataType = "distance",
                value = it.distance.inMeters,
                unit = "meters",
                recordedAt = it.endTime.atOffset(ZoneOffset.UTC).toString()
            )
        }
    }

    private suspend fun readCalories(timeRange: TimeRangeFilter): List<HealthDataRecord> {
        val response = client.readRecords(ReadRecordsRequest(TotalCaloriesBurnedRecord::class, timeRange))
        return response.records.map {
            HealthDataRecord(
                dataType = "calories",
                value = it.energy.inKilocalories,
                unit = "kcal",
                recordedAt = it.endTime.atOffset(ZoneOffset.UTC).toString()
            )
        }
    }

    private suspend fun readHeartRate(timeRange: TimeRangeFilter): List<HealthDataRecord> {
        val response = client.readRecords(ReadRecordsRequest(HeartRateRecord::class, timeRange))
        return response.records.flatMap { record ->
            record.samples.map { sample ->
                HealthDataRecord(
                    dataType = "heart_rate",
                    value = sample.beatsPerMinute.toDouble(),
                    unit = "bpm",
                    recordedAt = sample.time.atOffset(ZoneOffset.UTC).toString()
                )
            }
        }
    }

    private suspend fun readBloodPressure(timeRange: TimeRangeFilter): List<HealthDataRecord> {
        val response = client.readRecords(ReadRecordsRequest(BloodPressureRecord::class, timeRange))
        return response.records.flatMap {
            listOf(
                HealthDataRecord(
                    dataType = "blood_pressure_systolic",
                    value = it.systolic.inMillimetersOfMercury,
                    unit = "mmHg",
                    recordedAt = it.time.atOffset(ZoneOffset.UTC).toString()
                ),
                HealthDataRecord(
                    dataType = "blood_pressure_diastolic",
                    value = it.diastolic.inMillimetersOfMercury,
                    unit = "mmHg",
                    recordedAt = it.time.atOffset(ZoneOffset.UTC).toString()
                )
            )
        }
    }

    private suspend fun readBodyTemperature(timeRange: TimeRangeFilter): List<HealthDataRecord> {
        val response = client.readRecords(ReadRecordsRequest(BodyTemperatureRecord::class, timeRange))
        return response.records.map {
            HealthDataRecord(
                dataType = "body_temperature",
                value = it.temperature.inCelsius,
                unit = "celsius",
                recordedAt = it.time.atOffset(ZoneOffset.UTC).toString()
            )
        }
    }

    private suspend fun readWeight(timeRange: TimeRangeFilter): List<HealthDataRecord> {
        val response = client.readRecords(ReadRecordsRequest(WeightRecord::class, timeRange))
        return response.records.map {
            HealthDataRecord(
                dataType = "weight",
                value = it.weight.inKilograms,
                unit = "kg",
                recordedAt = it.time.atOffset(ZoneOffset.UTC).toString()
            )
        }
    }

    private suspend fun readSleep(timeRange: TimeRangeFilter): List<HealthDataRecord> {
        val response = client.readRecords(ReadRecordsRequest(SleepSessionRecord::class, timeRange))
        return response.records.map {
            val durationMinutes = java.time.Duration.between(it.startTime, it.endTime).toMinutes()
            HealthDataRecord(
                dataType = "sleep",
                value = durationMinutes.toDouble(),
                unit = "minutes",
                recordedAt = it.endTime.atOffset(ZoneOffset.UTC).toString()
            )
        }
    }
}
