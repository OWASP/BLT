#!/bin/sh
set PRODUCT_BUNDLE_IDENTIFIER="${PRODUCT_BUNDLE_IDENTIFIER:=com.apps.blt}"
set BASE_URL="${BASE_URL:=www.owasp.org/BLT/}"
set SENTRY_DSN="${SENTRY_DSN:=https://example-234234324.com/4504877879197696}"

sed -i.backup "s~www.owasp.org/BLT/~$BASE_URL~g" lib/src/util/endpoints/general_endpoints.dart
echo "sed BASE_URL"

sed -i.backup "s~https://example-234234324.com/4504877879197696~$SENTRY_DSN~g" lib/main.dart
echo "sed SENTRY_DSN"

sed -i.backup "s/com.apps.blt/$PRODUCT_BUNDLE_IDENTIFIER/g" ios/Runner.xcodeproj/project.pbxproj
echo "sed PRODUCT_BUNDLE_IDENTIFIER_1"

sed -i.backup "s/com.apps.blt/$PRODUCT_BUNDLE_IDENTIFIER/g" android/app/build.gradle 
echo "sed PRODUCT_BUNDLE_IDENTIFIER_2"

sed -i.backup "s/com.apps.blt/$PRODUCT_BUNDLE_IDENTIFIER/g" android/app/src/main/AndroidManifest.xml
echo "sed PRODUCT_BUNDLE_IDENTIFIER_3"
