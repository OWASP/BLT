import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/issue_model.dart';
import '../models/issuedata_model.dart';

import '../util/api/issues_api.dart';
import '../util/endpoints/issue_endpoints.dart';

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

  Future<void> getMoreIssues(String nextUrl) async {
    _cacheState();
    try {
      final IssueData? issueData = await IssueApiClient.getAllIssues(
        nextUrl,
      );
      print(issueData!.issueList);
      nxtUrl = issueData.nextQuery;
      state = state!.whenData((issueList) {
        issueList!.addAll(issueData.issueList!);
        return issueList;
      });
    } catch (e) {
      _handleException(e);
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
