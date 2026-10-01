package com.fotorestore.app

import android.content.ContentValues
import android.content.Intent
import android.graphics.Rect
import android.net.Uri
import android.os.Bundle
import android.os.Environment
import android.provider.MediaStore
import android.view.View
import android.widget.*
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.FileProvider
import androidx.lifecycle.lifecycleScope
import coil.load
import java.io.File
import kotlinx.coroutines.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody

class MainActivity : AppCompatActivity() {
    private lateinit var api: Api
    private var picked: Uri? = null
    private var jobId: String? = null
    private var resultFile: File? = null
    private lateinit var imgBefore: ImageView
    private lateinit var imgAfter: ImageView

    private val pickPhoto = registerForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        uri?.let { picked = it; imgBefore.load(it); imgAfter.setImageDrawable(null); setStatus("Siap. Tekan Enhance.") }
    }
    private val takePhoto = registerForActivityResult(ActivityResultContracts.TakePicture()) { ok ->
        if (ok) { picked?.let { imgBefore.load(it); imgAfter.setImageDrawable(null) }; setStatus("Siap. Tekan Enhance.") }
    }

    override fun onCreate(s: Bundle?) {
        super.onCreate(s)
        setContentView(R.layout.activity_main)
        val prefs = getSharedPreferences("fr", MODE_PRIVATE)
        api = Api.create(BuildConfig.API_BASE) { prefs.getString("token", "") ?: "" }
        findViewById<EditText>(R.id.etToken).setText(prefs.getString("token", ""))
        findViewById<Button>(R.id.btnToken).setOnClickListener {
            prefs.edit().putString("token", findViewById<EditText>(R.id.etToken).text.toString().trim()).apply()
            refreshQuota()
        }
        imgBefore = findViewById(R.id.imgBefore); imgAfter = findViewById(R.id.imgAfter)
        val seek: SeekBar = findViewById(R.id.seek)
        seek.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(sb: SeekBar?, p: Int, u: Boolean) = applyClip(p)
            override fun onStartTrackingTouch(sb: SeekBar?) {}
            override fun onStopTrackingTouch(sb: SeekBar?) {}
        })
        findViewById<Button>(R.id.btnPick).setOnClickListener { pickPhoto.launch("image/*") }
        findViewById<Button>(R.id.btnCamera).setOnClickListener {
            val f = File.createTempFile("cam", ".jpg", cacheDir)
            picked = FileProvider.getUriForFile(this, "$packageName.provider", f)
            takePhoto.launch(picked)
        }
        findViewById<Button>(R.id.btnGo).setOnClickListener { startEnhance() }
        findViewById<Button>(R.id.btnSave).setOnClickListener { saveToGallery() }
        findViewById<Button>(R.id.btnShare).setOnClickListener { share() }
        findViewById<Button>(R.id.btnDelete).setOnClickListener { deleteRemote() }
        refreshQuota()
    }

    private fun applyClip(p: Int) {
        imgAfter.post {
            val w = imgAfter.width
            imgAfter.clipBounds = Rect(0, 0, (w * p / 100f).toInt(), imgAfter.height)
        }
    }

    private fun setStatus(t: String) { findViewById<TextView>(R.id.tvStatus).text = t }
    private fun setProg(p: Int) { findViewById<ProgressBar>(R.id.prog).progress = p }

    private fun refreshQuota() {
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val m = api.me()
                val q = if (m.premium) "Premium (tanpa batas)" else "Gratis: ${m.quota.used}/${m.quota.limit} hari ini"
                withContext(Dispatchers.Main) { findViewById<TextView>(R.id.tvQuota).text = "Kuota: $q" }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) { findViewById<TextView>(R.id.tvQuota).text = "Kuota: butuh API key" }
            }
        }
    }

    private fun uriToFile(uri: Uri): File {
        val out = File.createTempFile("up", ".jpg", cacheDir)
        contentResolver.openInputStream(uri)!!.use { ins -> out.outputStream().use { ins.copyTo(it) } }
        return out
    }

    private fun startEnhance() {
        val uri = picked ?: run { setStatus("Pilih foto dulu"); return }
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                withContext(Dispatchers.Main) { setStatus("Upload..."); setProg(5) }
                val f = uriToFile(uri)
                val part = MultipartBody.Part.createFormData("file", f.name, f.asRequestBody("image/*".toMediaType()))
                val mode = findViewById<Spinner>(R.id.spMode).selectedItem.toString()
                val fid = 0.7f + findViewById<SeekBar>(R.id.seekFid).progress * 0.01f
                val gen = findViewById<CheckBox>(R.id.cbGen).isChecked
                if (gen && mode != "ultra") { withContext(Dispatchers.Main) { setStatus("Generatif hanya untuk mode ultra") }; return@launch }
                val en = api.enhance(part, mode.toRequestBody(), "medium".toRequestBody(), fid.toString().toRequestBody(), gen.toString().toRequestBody())
                jobId = en.job_id
                while (true) {
                    delay(2000)
                    val j = api.job(en.job_id)
                    withContext(Dispatchers.Main) { setProg(j.progress); setStatus("${j.status} ${j.progress}%") }
                    if (j.status == "completed") break
                    if (j.status == "failed") throw RuntimeException(j.error ?: "gagal")
                }
                val body = api.result(en.job_id)
                val out = File(cacheDir, "hasil_${en.job_id}.png")
                out.outputStream().use { body.byteStream().copyTo(it) }
                resultFile = out
                withContext(Dispatchers.Main) {
                    imgAfter.load(out); applyClip(findViewById<SeekBar>(R.id.seek).progress)
                    setStatus("Selesai. Geser slider untuk bandingkan."); setProg(100)
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) { setStatus("Error: ${e.message}") }
            }
        }
    }

    private fun saveToGallery() {
        val src = resultFile ?: run { setStatus("Belum ada hasil"); return }
        val vals = ContentValues().apply {
            put(MediaStore.Images.Media.DISPLAY_NAME, "fotorestore_${System.currentTimeMillis()}.png")
            put(MediaStore.Images.Media.MIME_TYPE, "image/png")
            put(MediaStore.Images.Media.RELATIVE_PATH, Environment.DIRECTORY_PICTURES + "/FotoRestore")
        }
        val uri = contentResolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, vals) ?: return
        contentResolver.openOutputStream(uri)!!.use { o -> src.inputStream().use { it.copyTo(o) } }
        setStatus("Tersimpan di Galeri.")
    }

    private fun share() {
        val src = resultFile ?: run { setStatus("Belum ada hasil"); return }
        val uri = FileProvider.getUriForFile(this, "$packageName.provider", src)
        startActivity(Intent.createChooser(Intent(Intent.ACTION_SEND).apply {
            type = "image/png"; putExtra(Intent.EXTRA_STREAM, uri)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }, "Bagikan"))
    }

    private fun deleteRemote() {
        val id = jobId ?: run { setStatus("Belum ada job"); return }
        lifecycleScope.launch(Dispatchers.IO) {
            try { api.delete(id); withContext(Dispatchers.Main) { setStatus("Hasil dihapus dari server.") } }
            catch (e: Exception) { withContext(Dispatchers.Main) { setStatus("Error: ${e.message}") } }
        }
    }
}
