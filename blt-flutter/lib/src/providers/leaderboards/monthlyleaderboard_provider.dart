import 'package:blt/src/models/leaderdata_model.dart';
import 'package:blt/src/providers/providers_imports.dart';
import 'package:http/http.dart' as http;

final monthlyLeaderBoardProvider = StateNotifierProvider<
    MonthlyLeaderBoardNotifier, AsyncValue<List<Leaders>?>?>((ref) {
  return MonthlyLeaderBoardNotifier(ref.read);
});

class MonthlyLeaderBoardNotifier
    extends StateNotifier<AsyncValue<List<Leaders>?>?> {
  final Reader read;
  String? nextUrl;
  AsyncValue<List<Leaders>?>? previousState;

  MonthlyLeaderBoardNotifier(this.read, [AsyncValue<List<Leaders>>? leaderList])
      : super(leaderList ?? const AsyncValue.loading()) {
    _retrieveMonthlyLeaderList(DateTime.now().year, DateTime.now().month);
  }

  Future<void> _retrieveMonthlyLeaderList(int? year, int? month) async {
    try {
      final LeaderData? monthlyLeaderData =
          await LeaderboardApiClient.getMonthlyLeaderData(
        http.Client(),
        LeaderboardEndpoints.monthly_leaderboard,
        year,
        month,
      );
      nextUrl = monthlyLeaderData!.nextQuery;
      state = AsyncValue.data(monthlyLeaderData.leaderList);
    } catch (e) {
      AsyncValue.error(e);
    }
  }

  Future<void> getMoreMontlyLeaders() async {
    _cacheState();
    try {
      final LeaderData leaderData =
          await LeaderboardApiClient.getMoreMonthlyLeaders(nextUrl);
      nextUrl = leaderData.nextQuery;
      state = state!.whenData((leaderList) {
        leaderList!.addAll(leaderData.leaderList!);
        return leaderList;
      });
    } catch (e) {
      _handleException(e);
    }
  }

  Future<void> refreshMonthlyLeaderList(int? year, int? month) async {
    state = const AsyncValue.loading();
    try {
      await _retrieveMonthlyLeaderList(year, month);
    } catch (e) {
      AsyncValue.error(e);
    }
  }

  /// Caches the current state to prevent errors.
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
