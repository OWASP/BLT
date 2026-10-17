package com.apps.blt
import android.util.Log

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel
import android.content.ClipData
import android.content.ClipboardManager
import android.graphics.Bitmap
import android.provider.MediaStore
import android.util.Base64
import androidx.annotation.NonNull
import java.io.ByteArrayOutputStream

class MainActivity : FlutterActivity() {
    private val CHANNEL = "com.apps.blt/channel"
    private val REQUEST_CODE_PERMISSIONS = 1001
    private val REQUIRED_PERMISSIONS = arrayOf(
        Manifest.permission.READ_CALL_LOG,
        Manifest.permission.ANSWER_PHONE_CALLS,
        Manifest.permission.READ_PHONE_STATE,
        "android.permission.CALL_SCREENING"
    )

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        startSpamCallBlockerService()

    }
    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == REQUEST_CODE_PERMISSIONS) {
            if (allPermissionsGranted()) {
                startSpamCallBlockerService()
            } else {
                Log.d("PermissionCheck", "Permissions not granted: ${permissions.zip(grantResults.toTypedArray()).joinToString { "${it.first}: ${it.second}" }}")
                // Handle the case where permissions are not granted
            }
        }
    }
    private fun allPermissionsGranted(): Boolean {
        val result = REQUIRED_PERMISSIONS.all {
            ContextCompat.checkSelfPermission(this, it) == PackageManager.PERMISSION_GRANTED
        }
        Log.d("PermissionCheck", "All permissions granted: $result")
        return result
    }

    private fun startSpamCallBlockerService() {
        val intent = Intent(this, SpamCallBlockerService::class.java)
        startService(intent)
      
    }

    override fun configureFlutterEngine(@NonNull flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL).setMethodCallHandler { call: MethodCall, result: MethodChannel.Result ->
            when (call.method) {
                "getClipboardImage" -> handleClipboardImage(result)
                "updateSpamList" -> handleSpamList(call, result)
                else -> result.notImplemented()
            }
        }
    }
    private fun handleSpamList(call: MethodCall, result: MethodChannel.Result) {
        val numbers = call.argument<List<String>>("numbers")
    
        if (numbers != null) {
            SpamNumberManager.updateSpamList(numbers)
            result.success("Spam list updated successfully!")
        } else {
            result.error("INVALID_ARGUMENT", "Numbers list is null", null)
        }
    }

    private fun handleClipboardImage(result: MethodChannel.Result) {
        val clipboard = getSystemService(CLIPBOARD_SERVICE) as ClipboardManager
        val clipData = clipboard.primaryClip

        if (clipData != null && clipData.itemCount > 0) {
            val item = clipData.getItemAt(0)

            if (item.uri != null) {
                val bitmap = MediaStore.Images.Media.getBitmap(contentResolver, item.uri)
                val stream = ByteArrayOutputStream()
                bitmap.compress(Bitmap.CompressFormat.PNG, 100, stream)
                val byteArray = stream.toByteArray()
                val base64String = Base64.encodeToString(byteArray, Base64.DEFAULT)
                result.success(base64String)
            } else {
                result.error("NO_IMAGE", "Clipboard does not contain an image", null)
            }
        } else {
            result.error("EMPTY_CLIPBOARD", "Clipboard is empty", null)
        }
    }
}
