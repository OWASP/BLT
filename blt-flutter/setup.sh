#!/bin/sh
set PRODUCT_BUNDLE_IDENTIFIER="${PRODUCT_BUNDLE_IDENTIFIER:=com.apps.blt}"
set BASE_URL="${BASE_URL:=www.owasp.org/BLT/}"
set SENTRY_DSN="${SENTRY_DSN:=https://example-234234324.com/4504877879197696}"

sed -i.backup "s~www.owasp.org/BLT/~$BASE_URL~g" lib/src/util/endpoints/general_endpoints.dart
sed -i.backup "s~https://example-234234324.com/4504877879197696~$SENTRY_DSN~g" lib/main.dart
sed -i.backup "s/com.apps.blt/$PRODUCT_BUNDLE_IDENTIFIER/g" ios/Runner.xcodeproj/project.pbxproj
sed -i.backup "s/com.apps.blt/$PRODUCT_BUNDLE_IDENTIFIER/g" android/app/build.gradle 
sed -i.backup "s/com.apps.blt/$PRODUCT_BUNDLE_IDENTIFIER/g" android/app/src/main/AndroidManifest.xml
