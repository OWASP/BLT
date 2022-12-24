import 'package:bugheist/src/models/leader_model.dart';
import 'package:bugheist/src/util/api/leaderboard_api.dart';
import 'package:bugheist/src/util/endpoints/leaderboard_endpoints.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// The provider which exposes the state management
/// for users in the global leaderboard list.
final globalLeaderBoardProvider = StateNotifierProvider<
    GlobalLeaderBoardNotifier, AsyncValue<List<Leaders>?>?>((ref) {
  return GlobalLeaderBoardNotifier(ref.read);
});

class GlobalLeaderBoardNotifier
    extends StateNotifier<AsyncValue<List<Leaders>?>?> {
  final Reader read;
  AsyncValue<List<Leaders>?>? previousState;

  GlobalLeaderBoardNotifier(this.read, [AsyncValue<List<Leaders>>? leaderList])
      : super(leaderList ?? const AsyncValue.loading()) {
    _retrieveLeaderList();
  }

  /// Default call for getting users in leaderboard
  /// when the provider is initialized.
  Future<void> _retrieveLeaderList() async {
    try {
      final List<Leaders>? leaderData =
          await LeaderboardApiClient.getLeaderData(
        LeaderboardEndpoints.globalLeaderboard,
      );

      state = AsyncValue.data(leaderData);
    } catch (e) {
      AsyncValue.error(e);
    }
  }

  /// Function call for refreshing state.
  Future<void> refreshLeaderList() async {
    state = const AsyncValue.loading();
    try {
      await _retrieveLeaderList();
    } catch (e) {
      AsyncValue.error(e);
    }
  }

  /// Caches the current state to prevent errors.
  void _cacheState() {
    previousState = state;
  }

  /// Resets the state to previous stored state.
  void _resetState() {
    if (previousState != null) {
      state = previousState;
      previousState = null;
    }
  }

  /// Exception handler for state exception,
  /// resets to last state on error.
  void _handleException(e) {
    print(e);
    _resetState();
  }
}
