import 'package:flutter/material.dart';

/// BLT is moving from its old backend (offline while its data is migrated) to
/// new services. Bug reports go to the BLT API; the rest is not available yet.
const String migrationNotice =
    "BLT is moving to a new platform. You can report bugs as a guest; "
    "sign-in, leaderboards, companies, bug hunts and profiles are not "
    "available yet. Data from the old site will be back after the migration.";

/// "<feature> is not available yet: ..."
String notAvailableYet(String feature) =>
    "$feature is not available yet: BLT is moving to a new platform.";

bool _migrationNoticeShown = false;

/// Show [migrationNotice] as a dismissible banner, once per app run.
void showMigrationNoticeOnce(BuildContext context) {
  if (_migrationNoticeShown) return;
  _migrationNoticeShown = true;
  final ScaffoldMessengerState messenger = ScaffoldMessenger.of(context);
  messenger.showMaterialBanner(
    MaterialBanner(
      content: const Text(migrationNotice),
      actions: <Widget>[
        TextButton(
          onPressed: () => messenger.hideCurrentMaterialBanner(),
          child: const Text("OK"),
        ),
      ],
    ),
  );
}

/// Tell the user that [feature] is not available yet.
void showNotAvailableYet(BuildContext context, String feature) {
  final ScaffoldMessengerState messenger = ScaffoldMessenger.of(context);
  messenger.clearSnackBars();
  messenger.showSnackBar(
    SnackBar(
      duration: const Duration(seconds: 6),
      content: Text(notAvailableYet(feature)),
    ),
  );
}
