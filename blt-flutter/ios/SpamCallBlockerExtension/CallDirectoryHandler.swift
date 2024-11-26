import CallKit

class CallDirectoryHandler: CXCallDirectoryProvider {
    override func beginRequest(with context: CXCallDirectoryExtensionContext) {
        // Access UserDefaults with App Group
        let userDefaults = UserDefaults(suiteName: "group.com.apps.blt.shared")
        
        // Retrieve the spam numbers
        if let spamNumbers = userDefaults?.array(forKey: "spamNumbers") as? [String] {
            // Convert the spam numbers to CXCallDirectoryPhoneNumber and sort them
            let blockedPhoneNumbers: [CXCallDirectoryPhoneNumber] = spamNumbers.compactMap { Int64($0) }.sorted(by: <)
            
            // Add sorted phone numbers to the blocking list
            for phoneNumber in blockedPhoneNumbers {
                context.addBlockingEntry(withNextSequentialPhoneNumber: phoneNumber)
            }
        }
        
        // Complete the request
        context.completeRequest()
    }
}
