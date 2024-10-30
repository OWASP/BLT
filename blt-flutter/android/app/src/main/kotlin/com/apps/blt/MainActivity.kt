package com.apps.blt

import android.content.ClipData
import android.content.ClipboardManager
import android.graphics.Bitmap
import android.graphics.drawable.BitmapDrawable
import android.os.Build
import android.provider.MediaStore
import android.util.Base64
import androidx.annotation.NonNull
import androidx.annotation.RequiresApi
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.io.ByteArrayOutputStream

class MainActivity : FlutterActivity() {
    private val CHANNEL = "clipboard_image_channel"

    override fun configureFlutterEngine(@NonNull flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL).setMethodCallHandler { call, result ->
            if (call.method == "getClipboardImage") {
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
            } else {
                result.notImplemented()
            }
        }
    }
}
