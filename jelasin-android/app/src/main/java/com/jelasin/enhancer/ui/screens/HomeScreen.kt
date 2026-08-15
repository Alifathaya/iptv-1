package com.jelasin.enhancer.ui.screens

import com.jelasin.enhancer.domain.model.HistoryItem
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.jelasin.enhancer.ui.viewmodel.HomeViewModel
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(
    viewModel: HomeViewModel,
    onNewEnhance: () -> Unit,
) {
    val state by viewModel.state.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("Jelasin", style = MaterialTheme.typography.headlineSmall)
                        Text(
                            "AI Photo Enhancer",
                            style = MaterialTheme.typography.labelMedium,
                            color = MaterialTheme.colorScheme.primary,
                        )
                    }
                },
            )
        },
        floatingActionButton = {
            FloatingActionButton(onClick = onNewEnhance) {
                Icon(Icons.Default.Add, contentDescription = "Perjelas foto baru")
            }
        },
    ) { padding ->
        if (state.history.isEmpty()) {
            Column(
                Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .padding(24.dp),
                verticalArrangement = Arrangement.Center,
            ) {
                Text(
                    "Ubah foto buram jadi jernih",
                    style = MaterialTheme.typography.titleLarge,
                )
                Text(
                    "Tap + untuk memilih galeri atau kamera",
                    style = MaterialTheme.typography.bodyMedium,
                    modifier = Modifier.padding(top = 8.dp),
                )
            }
        } else {
            LazyColumn(
                contentPadding = PaddingValues(
                    top = padding.calculateTopPadding() + 8.dp,
                    bottom = padding.calculateBottomPadding() + 80.dp,
                    start = 16.dp,
                    end = 16.dp,
                ),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                items(state.history, key = { it.id }) { item ->
                    HistoryCard(item = item, onDelete = { viewModel.deleteHistory(item.id) })
                }
            }
        }
    }
}

@Composable
private fun HistoryCard(item: HistoryItem, onDelete: () -> Unit) {
    val date = SimpleDateFormat("dd MMM yyyy HH:mm", Locale("id")).format(Date(item.createdAt))
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(12.dp)) {
            AsyncImage(
                model = File(item.enhancedPath),
                contentDescription = null,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(160.dp),
                contentScale = ContentScale.Crop,
            )
            Text(item.preset, style = MaterialTheme.typography.labelLarge, modifier = Modifier.padding(top = 8.dp))
            Text("${item.width}×${item.height} · $date", style = MaterialTheme.typography.bodySmall)
            IconButton(onClick = onDelete) {
                Icon(Icons.Default.Delete, contentDescription = "Hapus")
            }
        }
    }
}
