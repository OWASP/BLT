import 'package:bugheist/util/enums/login_type.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

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
