import 'dart:ffi' as ffi;
import 'dart:io';
import 'package:ffi/ffi.dart';

// C function signatures
typedef InitTrackingNative = ffi.Int32 Function();
typedef InitTrackingDart = int Function();

typedef ProcessEventsNative = ffi.Void Function();
typedef ProcessEventsDart = void Function();

typedef GetActivityDataNative = ffi.Void Function(
    ffi.Pointer<ffi.Int32> keyCount, ffi.Pointer<ffi.Double> mouseDistance);
typedef GetActivityDataDart = void Function(
    ffi.Pointer<ffi.Int32> keyCount, ffi.Pointer<ffi.Double> mouseDistance);

typedef GetExtendedActivityDataNative = ffi.Void Function(
  ffi.Pointer<ffi.Int32> keyCount,
  ffi.Pointer<ffi.Double> mouseDistance,
  ffi.Pointer<ffi.Int32> leftClicks,
  ffi.Pointer<ffi.Int32> rightClicks,
  ffi.Pointer<ffi.Double> scrollAmount,
  ffi.Pointer<ffi.Int32> enterCount);
typedef GetExtendedActivityDataDart = void Function(
  ffi.Pointer<ffi.Int32> keyCount,
  ffi.Pointer<ffi.Double> mouseDistance,
  ffi.Pointer<ffi.Int32> leftClicks,
  ffi.Pointer<ffi.Int32> rightClicks,
  ffi.Pointer<ffi.Double> scrollAmount,
  ffi.Pointer<ffi.Int32> enterCount);

typedef ResetActivityNative = ffi.Void Function();
typedef ResetActivityDart = void Function();

typedef CleanupTrackingNative = ffi.Void Function();
typedef CleanupTrackingDart = void Function();

class ActivityTrackerNative {
  late ffi.DynamicLibrary _lib;
  late InitTrackingDart _initTracking;
  late ProcessEventsDart _processEvents;
  late GetActivityDataDart _getActivityData;
  GetExtendedActivityDataDart? _getExtendedActivityData;
  late ResetActivityDart _resetActivity;
  late CleanupTrackingDart _cleanupTracking;

  ActivityTrackerNative() {
    // Load the shared library
    final libraryPath = Platform.script.resolve('linux/libactivity_tracker.so').toFilePath();
    try {
      _lib = ffi.DynamicLibrary.open(libraryPath);
    } catch (e) {
      // Try alternative path
      _lib = ffi.DynamicLibrary.open('linux/libactivity_tracker.so');
    }

    // Load functions
    _initTracking = _lib
        .lookup<ffi.NativeFunction<InitTrackingNative>>('init_tracking')
        .asFunction();

    _processEvents = _lib
        .lookup<ffi.NativeFunction<ProcessEventsNative>>('process_events')
        .asFunction();

    _getActivityData = _lib
        .lookup<ffi.NativeFunction<GetActivityDataNative>>('get_activity_data')
        .asFunction();

    // Extended function (optional if older lib present)
    try {
      _getExtendedActivityData = _lib
          .lookup<ffi.NativeFunction<GetExtendedActivityDataNative>>("get_extended_activity_data")
          .asFunction();
    } catch (e) {
      _getExtendedActivityData = null; // Fallback
    }

    _resetActivity = _lib
        .lookup<ffi.NativeFunction<ResetActivityNative>>('reset_activity')
        .asFunction();

    _cleanupTracking = _lib
        .lookup<ffi.NativeFunction<CleanupTrackingNative>>('cleanup_tracking')
        .asFunction();
  }

  bool initialize() {
    return _initTracking() == 1;
  }

  void processEvents() {
    _processEvents();
  }

  Map<String, dynamic> getActivityData() {
    final keyCountPtr = calloc<ffi.Int32>();
    final mouseDistancePtr = calloc<ffi.Double>();
    final leftClicksPtr = calloc<ffi.Int32>();
    final rightClicksPtr = calloc<ffi.Int32>();
    final scrollAmountPtr = calloc<ffi.Double>();
    final enterCountPtr = calloc<ffi.Int32>();

    try {
      if (_getExtendedActivityData != null) {
        _getExtendedActivityData!(
            keyCountPtr,
            mouseDistancePtr,
            leftClicksPtr,
            rightClicksPtr,
            scrollAmountPtr,
            enterCountPtr);
      } else {
        _getActivityData(keyCountPtr, mouseDistancePtr);
      }
      return {
        'keyCount': keyCountPtr.value,
        'mouseDistance': mouseDistancePtr.value,
        'leftClicks': leftClicksPtr.value,
        'rightClicks': rightClicksPtr.value,
        'scrollAmount': scrollAmountPtr.value,
        'enterCount': enterCountPtr.value,
      };
    } finally {
      calloc.free(keyCountPtr);
      calloc.free(mouseDistancePtr);
      calloc.free(leftClicksPtr);
      calloc.free(rightClicksPtr);
      calloc.free(scrollAmountPtr);
      calloc.free(enterCountPtr);
    }
  }

  void resetActivity() {
    _resetActivity();
  }

  void cleanup() {
    _cleanupTracking();
  }
}
