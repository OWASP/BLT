import 'package:permission_handler/permission_handler.dart';

Future<void> requestStoragePermission() async {
  if (await Permission.photos.request().isGranted) {
    return;
  } else if (await Permission.photos.request().isDenied) {
    return;
  } else {
    Permission.photos.request();
  }
}
