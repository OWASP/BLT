import Flutter
import UIKit

@main
@objc class AppDelegate: FlutterAppDelegate {
  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    // Register the method channel
    let controller = window?.rootViewController as! FlutterViewController
    let clipboardImageChannel = FlutterMethodChannel(name: "com.apps.blt/channel",
                                                      binaryMessenger: controller.binaryMessenger)

    clipboardImageChannel.setMethodCallHandler { (call: FlutterMethodCall, result: @escaping FlutterResult) in
      if call.method == "getClipboardImage" {
        self.getClipboardImage(result: result)
      } else {
        result(FlutterMethodNotImplemented)
      }
    }

    GeneratedPluginRegistrant.register(with: self)
    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }

  private func getClipboardImage(result: FlutterResult) {
    // Check if the clipboard contains an image
    if let image = UIPasteboard.general.image {
      // Convert the image to PNG data
      if let imageData = image.pngData() {
        // Encode the image data to a Base64 string
        let base64String = imageData.base64EncodedString()
        result(base64String) // Send the Base64 string back to Flutter
      } else {
        result(FlutterError(code: "NO_IMAGE", message: "Could not convert image to data", details: nil))
      }
    } else {
      result(FlutterError(code: "NO_IMAGE", message: "Clipboard does not contain an image", details: nil))
    }
  }
}