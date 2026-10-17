import 'package:blt/src/providers/providers_imports.dart';

final bugHuntListProvider =
    StateNotifierProvider<BugHuntListProvider, AsyncValue<List<BugHunt>?>?>(
  (ref) {
    return BugHuntListProvider(ref.read);
  },
);

final prevBugHuntListProvider = StateNotifierProvider<
    PreviousBugHuntListProvider, AsyncValue<List<BugHunt>?>?>(
  (ref) {
    return PreviousBugHuntListProvider(ref.read);
  },
);

class BugHuntListProvider extends StateNotifier<AsyncValue<List<BugHunt>?>?> {
  final Reader read;
  AsyncValue<List<BugHunt>?>? previousState;

  BugHuntListProvider(this.read, [AsyncValue<List<BugHunt>>? bugHuntList])
      : super(bugHuntList ?? const AsyncValue.loading()) {
    _retrieveBugHuntsList();
  }

  Future<void> _retrieveBugHuntsList() async {
    try {
      final List<BugHunt>? bugHunts =
          await BugHuntApiClient.getListOfActiveBugHunts();
      state = AsyncValue.data(bugHunts);
    } catch (e) {
      AsyncValue.error(e);
    }
  }

  // Function call for refreshing state.
  Future<void> refreshBugHuntList() async {
    state = const AsyncValue.loading();
    try {
      await _retrieveBugHuntsList();
    } catch (e) {
      AsyncValue.error(e);
    }
  }
}

class PreviousBugHuntListProvider
    extends StateNotifier<AsyncValue<List<BugHunt>?>?> {
  final Reader read;
  AsyncValue<List<BugHunt>?>? previousState;

  PreviousBugHuntListProvider(this.read,
      [AsyncValue<List<BugHunt>>? bugHuntList])
      : super(bugHuntList ?? const AsyncValue.loading()) {
    _retrievePrevBugHuntsList();
  }

  Future<void> _retrievePrevBugHuntsList() async {
    try {
      final List<BugHunt>? bugHunts =
          await BugHuntApiClient.getListOfPreviousBugHunts();
      state = AsyncValue.data(bugHunts);
    } catch (e) {
      AsyncValue.error(e);
    }
  }

  // Function call for refreshing state.
  Future<void> refreshPrevBugHuntList() async {
    state = const AsyncValue.loading();
    try {
      await _retrievePrevBugHuntsList();
    } catch (e) {
      AsyncValue.error(e);
    }
  }
}
