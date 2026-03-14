package com.healthanalysis

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.*
import androidx.health.connect.client.PermissionController
import androidx.lifecycle.lifecycleScope
import com.healthanalysis.data.HealthDataRepository
import com.healthanalysis.data.SyncService
import com.healthanalysis.ui.HomeScreen
import com.healthanalysis.ui.PermissionsScreen
import com.healthanalysis.ui.SyncState
import kotlinx.coroutines.launch
import java.time.Instant

class MainActivity : ComponentActivity() {

    private lateinit var healthConnectManager: HealthConnectManager
    private lateinit var repository: HealthDataRepository
    private lateinit var syncService: SyncService

    // Points to the Termux backend running on the same phone
    private val backendUrl = "http://127.0.0.1:8000/"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        healthConnectManager = HealthConnectManager(this)
        repository = HealthDataRepository(this, healthConnectManager)
        syncService = SyncService(backendUrl)

        val requestPermissions = registerForActivityResult(
            PermissionController.createRequestPermissionResultContract()
        ) { granted ->
            lifecycleScope.launch { checkPermissionsAndSetContent() }
        }

        lifecycleScope.launch {
            checkPermissionsAndSetContent(
                onRequestPermissions = { requestPermissions.launch(healthConnectManager.permissions) }
            )
        }
    }

    private suspend fun checkPermissionsAndSetContent(
        onRequestPermissions: (() -> Unit)? = null
    ) {
        val hasPerms = healthConnectManager.hasAllPermissions()

        setContent {
            MaterialTheme {
                if (hasPerms) {
                    var syncState by remember {
                        mutableStateOf(
                            SyncState(lastSync = repository.getLastSyncTime().takeIf { it.toEpochMilli() > 0 })
                        )
                    }

                    HomeScreen(
                        syncState = syncState,
                        onSyncClick = {
                            lifecycleScope.launch {
                                syncState = syncState.copy(isLoading = true)
                                val result = syncService.sync(repository)
                                result.fold(
                                    onSuccess = { response ->
                                        syncState = syncState.copy(
                                            isLoading = false,
                                            lastSync = Instant.now(),
                                            lastResult = "Synced ${response.inserted} records"
                                        )
                                    },
                                    onFailure = { error ->
                                        syncState = syncState.copy(
                                            isLoading = false,
                                            lastResult = "Error: ${error.message}"
                                        )
                                    }
                                )
                            }
                        }
                    )
                } else {
                    PermissionsScreen(
                        onRequestPermissions = { onRequestPermissions?.invoke() }
                    )
                }
            }
        }
    }
}
