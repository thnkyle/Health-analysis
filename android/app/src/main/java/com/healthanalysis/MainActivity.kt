package com.healthanalysis

import android.os.Bundle
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
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

    private val backendUrl = "http://127.0.0.1:8000/"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        healthConnectManager = HealthConnectManager(this)
        repository = HealthDataRepository(this, healthConnectManager)
        syncService = SyncService(backendUrl)

        // Restore token if already logged in
        repository.getToken()?.let { syncService.setToken(it) }

        val requestPermissions = registerForActivityResult(
            PermissionController.createRequestPermissionResultContract()
        ) { _ ->
            lifecycleScope.launch { checkPermissionsAndSetContent() }
        }

        lifecycleScope.launch {
            ensureLoggedIn()
            checkPermissionsAndSetContent(
                onRequestPermissions = { requestPermissions.launch(healthConnectManager.permissions) }
            )
        }
    }

    /**
     * Auto-registers and logs in a local user on first launch.
     * On subsequent launches, restores the saved token.
     */
    private suspend fun ensureLoggedIn() {
        if (repository.isLoggedIn()) return

        val username = "local_user"
        val password = "local_device_password"

        // Try to register (will fail silently if account already exists)
        syncService.register(username, password)

        syncService.login(username, password).fold(
            onSuccess = { token ->
                repository.saveToken(token)
                repository.saveUsername(username)
            },
            onFailure = { error ->
                Log.e("MainActivity", "Auto-login failed: ${error.message}")
            }
        )
    }

    private suspend fun checkPermissionsAndSetContent(
        onRequestPermissions: (() -> Unit)? = null
    ) {
        val hasPerms = healthConnectManager.hasAllPermissions()

        setContent {
            MaterialTheme {
                if (!hasPerms) {
                    PermissionsScreen(
                        onRequestPermissions = { onRequestPermissions?.invoke() }
                    )
                } else {
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
                }
            }
        }
    }
}
