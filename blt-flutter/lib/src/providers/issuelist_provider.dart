import 'package:blt/src/providers/providers_imports.dart';
import 'package:http/http.dart' as http;

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
  final client = http.Client();

  /// Default call for getting first page of issues
  /// when the provider is initialized.
  Future<void> _retrieveIssueList() async {
    try {
      // final IssueData? issueData = await IssueApiClient.getAllIssues(
      //   client,
      //   IssueEndPoints.issues,
      // );
      // nxtUrl = issueData!.nextQuery;
      // state = AsyncValue.data(issueData.issueList);
    } catch (e) {
      AsyncValue.error(e);
    }
  }

  /// Function call for lazy loading next issues.
  Future<void> getMoreIssues(String nextUrl) async {
    _cacheState();
    try {
      final IssueData? issueData = await IssueApiClient.getAllIssues(
        client,
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

class IssueByStatusListProvider
    extends StateNotifier<AsyncValue<List<Issue>?>?> {
  final Reader read;
  final String status;
  final String? url;
  String? nxtUrl;
  AsyncValue<List<Issue>?>? previousState;

  IssueByStatusListProvider(this.read, this.status, this.url,
      [AsyncValue<List<Issue>>? issueList])
      : super(issueList ?? const AsyncValue.loading()) {
    _retrieveIssueList();
  }

  Future<void> _retrieveIssueList() async {
    try {
      final IssueData? issueData =
          await IssueApiClient.getIssueByStatus(status, url ?? "");
      state = AsyncValue.data(issueData?.issueList ?? []);
      print("Retrieved: ${state?.asData?.value}");
    } catch (e) {
      state = AsyncValue.error(e);
    }
  }

  Future<List<Issue>> getMoreIssues(String status, String? url) async {
    List<Issue> issues = [];
    _cacheState();
    try {
      final IssueData? issueData =
          await IssueApiClient.getIssueByStatus(status, url ?? "");
      issues = issueData?.issueList ?? [];
    } catch (e) {
      _handleException(e);
      throw e;
    }
    return issues;
  }

  Future<void> refreshIssueList() async {
    state = const AsyncValue.loading();
    try {
      await _retrieveIssueList();
    } catch (e) {
      AsyncValue.error(e);
    }
  }

  void _cacheState() {
    previousState = state;
  }

  void _resetState() {
    if (previousState != null) {
      state = previousState;
      previousState = null;
    }
  }

  void _handleException(e) {
    print(e);
    _resetState();
  }
}
