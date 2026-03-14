package com.healthanalysis.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter

data class SyncState(
    val isLoading: Boolean = false,
    val lastSync: Instant? = null,
    val lastResult: String = "",
    val recordCounts: Map<String, Int> = emptyMap()
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(
    syncState: SyncState,
    onSyncClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Scaffold(
        topBar = {
            TopAppBar(title = { Text("Health Analysis") })
        }
    ) { padding ->
        Column(
            modifier = modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            // Sync button
            Button(
                onClick = onSyncClick,
                enabled = !syncState.isLoading,
                modifier = Modifier.fillMaxWidth()
            ) {
                if (syncState.isLoading) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(20.dp),
                        strokeWidth = 2.dp
                    )
                    Spacer(Modifier.width(8.dp))
                    Text("Syncing...")
                } else {
                    Text("Sync Health Data")
                }
            }

            Spacer(Modifier.height(16.dp))

            // Last sync info
            syncState.lastSync?.let { instant ->
                val formatted = DateTimeFormatter
                    .ofPattern("MMM dd, yyyy HH:mm")
                    .withZone(ZoneId.systemDefault())
                    .format(instant)
                Text("Last sync: $formatted", style = MaterialTheme.typography.bodyMedium)
            }

            if (syncState.lastResult.isNotEmpty()) {
                Spacer(Modifier.height(8.dp))
                Text(syncState.lastResult, style = MaterialTheme.typography.bodySmall)
            }

            Spacer(Modifier.height(24.dp))

            // Data type summary
            if (syncState.recordCounts.isNotEmpty()) {
                Text("Synced Data", style = MaterialTheme.typography.titleMedium)
                Spacer(Modifier.height(8.dp))
                LazyColumn {
                    items(syncState.recordCounts.entries.toList()) { (type, count) ->
                        Card(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 4.dp)
                        ) {
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(16.dp),
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                Text(type.replace("_", " ").replaceFirstChar { it.uppercase() })
                                Text("$count records")
                            }
                        }
                    }
                }
            }
        }
    }
}
