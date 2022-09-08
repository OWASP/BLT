import 'package:bugheist/src/util/enums/login_type.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// The provider which exposes the state management for
/// the type of login (guest or user or logged out).
final loginProvider = StateNotifierProvider<LoginNotifier, LoginType>((ref) {
  return LoginNotifier(ref.read);
});

class LoginNotifier extends StateNotifier<LoginType> {
  final Reader read;
  LoginNotifier(this.read, [LoginType? state])
      : super(state ?? LoginType.loggedOut);

  /// Set login state to guest type.
  void setGuestLogin() {
    state = LoginType.guest;
  }

  /// Set login state to user type.
  void setUserLogin() {
    state = LoginType.user;
  }

  /// Set login state to logged out.
  void logout() {
    state = LoginType.loggedOut;
  }

  /// Getter for current login state.
  LoginType get loginType => state;
}
