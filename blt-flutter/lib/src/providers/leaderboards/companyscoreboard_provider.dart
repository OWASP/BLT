import 'package:bugheist/src/models/company_model.dart';
import 'package:bugheist/src/util/api/leaderboard_api.dart';
import 'package:bugheist/src/util/endpoints/leaderboard_endpoints.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// The provider which exposes the state management
/// for companies in the company scoreboard list.
final companyScoreboardProvider = StateNotifierProvider<
    CompanyScoreboardNotifier, AsyncValue<List<Company>?>?>((ref) {
  return CompanyScoreboardNotifier(ref.read);
});

class CompanyScoreboardNotifier
    extends StateNotifier<AsyncValue<List<Company>?>?> {
  final Reader read;
  AsyncValue<List<Company>?>? previousState;

  CompanyScoreboardNotifier(this.read, [AsyncValue<List<Company>>? companyList])
      : super(companyList ?? const AsyncValue.loading()) {
    _retrieveCompanyList();
  }

  /// Default call for getting companies
  /// when the provider is initialized.
  Future<void> _retrieveCompanyList() async {
    try {
      final List<Company>? companyData =
          await LeaderboardApiClient.getScoreBoardData(
        LeaderboardEndpoints.companyScoreboard,
      );

      state = AsyncValue.data(companyData);
    } catch (e) {
      AsyncValue.error(e);
    }
  }

  /// Function call for refreshing state.
  Future<void> refreshCompanyList() async {
    state = const AsyncValue.loading();
    try {
      await _retrieveCompanyList();
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
