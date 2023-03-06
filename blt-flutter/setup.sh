#!/bin/sh
set PRODUCT_BUNDLE_IDENTIFIER="${PRODUCT_BUNDLE_IDENTIFIER:=com.apps.blt}"

sed -i.backup "s/com.apps.blt/$PRODUCT_BUNDLE_IDENTIFIER/g" ios/Runner.xcodeproj/project.pbxproj
sed -i.backup "s/com.apps.blt/$PRODUCT_BUNDLE_IDENTIFIER/g" android/app/build.gradle 
sed -i.backup "s/com.apps.blt/$PRODUCT_BUNDLE_IDENTIFIER/g" android/app/src/main/AndroidManifest.xml
