import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/issue_model.dart';
import '../models/issuedata_model.dart';

import '../util/api/issues_api.dart';
import '../util/endpoints/issue_endpoints.dart';

/// The provider which exposes the state management
/// for issues in the issue list.
final issueListProvider =
    StateNotifierProvider<IssueListProvider, AsyncValue<List<Issue>?>?>((ref) {
  return IssueListProvider(ref.read);
});

class IssueListProvider extends StateNotifier<AsyncValue<List<Issue>?>?> {
  final Reader read;
  String? nxtUrl;
  AsyncValue<List<Issue>?>? previousState;

  IssueListProvider(this.read, [AsyncValue<List<Issue>>? issueList])
      : super(issueList ?? const AsyncValue.loading()) {
    _retrieveIssueList();
  }

  /// Default call for getting first page of issues
  /// when the provider is initialized.
  Future<void> _retrieveIssueList() async {
    try {
      final IssueData? issueData = await IssueApiClient.getAllIssues(
        IssueEndPoints.issues,
      );
      nxtUrl = issueData!.nextQuery;
      state = AsyncValue.data(issueData.issueList);
    } catch (e) {
      AsyncValue.error(e);
    }
  }

  /// Function call for lazy loading next issues.
  Future<void> getMoreIssues(String nextUrl) async {
    _cacheState();
    try {
      final IssueData? issueData = await IssueApiClient.getAllIssues(
        nextUrl,
      );

      nxtUrl = issueData!.nextQuery;
      state = state!.whenData((issueList) {
        issueList!.addAll(issueData.issueList!);
        return issueList;
      });
    } catch (e) {
      _handleException(e);
    }
  }

  /// Function call for refreshing state.
  Future<void> refreshIssueList() async {
    state = const AsyncValue.loading();
    try {
      await _retrieveIssueList();
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
