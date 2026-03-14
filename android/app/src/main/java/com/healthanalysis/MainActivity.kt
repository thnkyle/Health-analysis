package com.healthanalysis

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.*
import androidx.health.connect.client.PermissionController
import androidx.lifecycle.lifecycleScope
import com.healthanalysis.data.HealthDataRepository
import com.healthanalysis.data.SyncService
import com.healthanalysis.ui.HomeScreen
import com.healthanalysis.ui.LoginScreen
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

        // Restore token if logged in
        repository.getToken()?.let { syncService.setToken(it) }

        val requestPermissions = registerForActivityResult(
            PermissionController.createRequestPermissionResultContract()
        ) { _ ->
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
                var isLoggedIn by remember { mutableStateOf(repository.isLoggedIn()) }
                var authError by remember { mutableStateOf<String?>(null) }
                var authLoading by remember { mutableStateOf(false) }

                if (!isLoggedIn) {
                    LoginScreen(
                        onLogin = { username, password ->
                            lifecycleScope.launch {
                                authLoading = true
                                authError = null
                                syncService.login(username, password).fold(
                                    onSuccess = { token ->
                                        repository.saveToken(token)
                                        repository.saveUsername(username)
                                        isLoggedIn = true
                                    },
                                    onFailure = { authError = "Login failed: ${it.message}" }
                                )
                                authLoading = false
                            }
                        },
                        onRegister = { username, password ->
                            lifecycleScope.launch {
                                authLoading = true
                                authError = null
                                syncService.register(username, password).fold(
                                    onSuccess = {
                                        // Auto-login after registration
                                        syncService.login(username, password).fold(
                                            onSuccess = { token ->
                                                repository.saveToken(token)
                                                repository.saveUsername(username)
                                                isLoggedIn = true
                                            },
                                            onFailure = { authError = "Registration succeeded but login failed" }
                                        )
                                    },
                                    onFailure = { authError = "Registration failed: ${it.message}" }
                                )
                                authLoading = false
                            }
                        },
                        errorMessage = authError,
                        isLoading = authLoading
                    )
                } else if (!hasPerms) {
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
