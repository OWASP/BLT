import Flutter
import UIKit
// import Shared
import CallKit

@main
@objc class AppDelegate: FlutterAppDelegate {
    override func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
    ) -> Bool {
        let controller = window?.rootViewController as! FlutterViewController
        let spamChannel = FlutterMethodChannel(name: "com.apps.blt/channel", binaryMessenger: controller.binaryMessenger)

        spamChannel.setMethodCallHandler { (call: FlutterMethodCall, result: @escaping FlutterResult) in
            switch call.method {
            case "updateSpamList":
                if let args = call.arguments as? [String: Any],
                   let numbers = args["numbers"] as? [String] {
                    // Update the spam list in shared user preferences
                    let userDefaults = UserDefaults(suiteName: "group.com.apps.blt.shared")
                    userDefaults?.set(numbers, forKey: "spamNumbers")
                    print("Spam list updated: \(numbers)")
                    
                    // Reload the Call Directory extension
                    self.reloadCallDirectoryExtension(result: result)
                } else {
                    result(FlutterError(code: "INVALID_ARGUMENT", message: "Invalid numbers list", details: nil))
                }
                
            case "getClipboardImage":
                if let clipboardImage = UIPasteboard.general.image {
                    if let imageData = clipboardImage.pngData() {
                        let base64String = imageData.base64EncodedString()
                        result(base64String)
                    } else {
                        result(FlutterError(code: "NO_IMAGE", message: "Could not encode image", details: nil))
                    }
                } else {
                    result(FlutterError(code: "EMPTY_CLIPBOARD", message: "Clipboard is empty or does not contain an image", details: nil))
                }
                
            default:
                result(FlutterMethodNotImplemented)
            }
        }

        GeneratedPluginRegistrant.register(with: self)
        
        // Check the CallKit extension status
        checkExtensionStatus()
        
        return super.application(application, didFinishLaunchingWithOptions: launchOptions)
    }
    
    // Function to check the CallKit extension status
    func checkExtensionStatus() {
        let extensionIdentifier = "com.krrishsehgal.blt.SpamCallBlockerExtension"
        CXCallDirectoryManager.sharedInstance.getEnabledStatusForExtension(withIdentifier: extensionIdentifier) { (status, error) in
            if let error = error {
                print("Error checking extension status: \(error.localizedDescription)")
            } else {
                switch status {
                case .enabled:
                    print("Extension is enabled.")
                case .disabled:
                    print("Extension is disabled.")
                    self.openExtensionSettings()
                default:
                    print("Unknown extension status.")
                }
            }
        }
    }
    
    // Function to open the Settings page for the CallKit extension
    func openExtensionSettings() {
        if #available(iOS 13.4, *) {
            CXCallDirectoryManager.sharedInstance.openSettings { error in
                if let error = error {
                    print("Error opening settings: \(error.localizedDescription)")
                } else {
                    print("Opened Settings for extension.")
                }
            }
        } else {
            print("Settings cannot be opened on iOS versions earlier than 13.4.")
        }
    }
    
    // Reload Call Directory Extension
    func reloadCallDirectoryExtension(result: @escaping FlutterResult) {
        let extensionIdentifier = "com.krrishsehgal.blt.SpamCallBlockerExtension"
        CXCallDirectoryManager.sharedInstance.reloadExtension(withIdentifier: extensionIdentifier) { error in
            if let error = error {
                print("Failed to reload Call Directory Extension: \(error.localizedDescription)")
                result(FlutterError(code: "RELOAD_FAILED", message: error.localizedDescription, details: nil))
            } else {
                print("Successfully reloaded Call Directory Extension!")
                result("Call Directory Extension reloaded successfully!")
            }
        }
    }
}
