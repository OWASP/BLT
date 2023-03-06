#!/bin/sh
set PRODUCT_BUNDLE_IDENTIFIER="${PRODUCT_BUNDLE_IDENTIFIER:=com.apps.blt}"
set BASE_URL="${BASE_URL:=www.owasp.org/BLT/}"

sed -i.backup "s~www.owasp.org/BLT/~$BASE_URL~g" lib/src/util/endpoints/general_endpoints.dart
sed -i.backup "s/com.apps.blt/$PRODUCT_BUNDLE_IDENTIFIER/g" ios/Runner.xcodeproj/project.pbxproj
sed -i.backup "s/com.apps.blt/$PRODUCT_BUNDLE_IDENTIFIER/g" android/app/build.gradle 
sed -i.backup "s/com.apps.blt/$PRODUCT_BUNDLE_IDENTIFIER/g" android/app/src/main/AndroidManifest.xml
