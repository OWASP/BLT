import 'package:flutter_riverpod/flutter_riverpod.dart';

final issueLikeProvider = StateNotifierProvider<IssueLikeNotifier, Map>(
  ((ref) => IssueLikeNotifier(ref.read)),
);
var issueFlagProvider;

class IssueLikeNotifier extends StateNotifier<Map> {
  final Reader read;
  Map? previousState;

  IssueLikeNotifier(this.read, [Map? likeState])
      : super(likeState ?? {'likeCount': 0, 'liked': false});
}

class IssueFlagNotifier {}
