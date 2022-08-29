import 'package:bugheist/src/util/enums/login_type.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// The provider which exposes the state management for
/// the type of login (guest or user).
final loginProvider = StateNotifierProvider<LoginNotifier, LoginType>((ref) {
  return LoginNotifier(ref.read);
});

class LoginNotifier extends StateNotifier<LoginType> {
  final Reader read;
  LoginNotifier(this.read, [LoginType? state])
      : super(state ?? LoginType.loggedOut);
  void setGuestLogin() {
    state = LoginType.guest;
  }

  void setUserLogin() {
    state = LoginType.user;
  }

  void logout() {
    state = LoginType.loggedOut;
  }

  LoginType get loginType => state;
}
