import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import './login_provider.dart';
import '../models/user_model.dart';
import '../routes/routing.dart';
import '../global/variables.dart';
import '../util/api/auth_api.dart';
import '../util/enums/authstate_type.dart';
import '../util/enums/login_type.dart';

final authStateNotifier =
    StateNotifierProvider<AuthNotifier, AsyncValue<AuthState>>((ref) {
  return AuthNotifier(ref.read);
});

class AuthNotifier extends StateNotifier<AsyncValue<AuthState>> {
  final Reader read;
  AsyncValue<AuthState>? previousState;

  AuthNotifier(this.read, [AsyncValue<AuthState>? authstate])
      : super(
          authstate ?? const AsyncValue.data(AuthState.loggedOut),
        );

  void guestLogin() {
    state = AsyncValue.data(AuthState.loggedIn);
    currentUser = guestUser;
    read(loginProvider.notifier).setGuestLogin();
  }

  Future<void> userLogin(
      Map<String, String?> userCreds, BuildContext parentContext) async {
    state = AsyncValue.data(AuthState.authenticating);
    try {
      currentUser = await AuthApiClient.login(userCreds);

      state = AsyncValue.data(AuthState.loggedIn);
      read(loginProvider.notifier).setUserLogin();

      Navigator.of(parentContext).pushNamed(
        RouteManager.homePage,
      );
    } catch (e) {}
  }

  Future<void> logout() async {
    LoginType loginType = read(loginProvider.notifier).loginType;
    if (loginType == LoginType.guest) {
      await Future.delayed(const Duration(seconds: 1));
      state = AsyncValue.data(AuthState.loggedOut);
      read(loginProvider.notifier).logout();
      currentUser = null;
    } else if (loginType == LoginType.user) {
      if (await AuthApiClient.logout()) {
        await Future.delayed(const Duration(seconds: 1));
        state = AsyncValue.data(AuthState.loggedOut);
        read(loginProvider.notifier).logout();
        currentUser = null;
      }
    }
  }

  Future<void> signup() async {}
}
