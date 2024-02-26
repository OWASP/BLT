import 'package:blt/src/providers/providers_imports.dart';

/// The provider which exposes the state management for user authentication.
final authStateNotifier =
    StateNotifierProvider<AuthNotifier, AsyncValue<AuthState>>((ref) {
  return AuthNotifier(ref.read);
});

class AuthNotifier extends StateNotifier<AsyncValue<AuthState>> {
  final Reader read;
  AsyncValue<AuthState>? previousState;
  final storage = new FlutterSecureStorage();

  AuthNotifier(this.read, [AsyncValue<AuthState>? authstate])
      : super(
          authstate ?? const AsyncValue.data(AuthState.loggedOut),
        );

  /// Do a guest type authentication.
  Future<void> guestLogin() async {
    await storage.write(
      key: "remember",
      value: "guest",
    );
    state = AsyncValue.data(AuthState.loggedIn);
    currentUser = guestUser;
    read(loginProvider.notifier).setGuestLogin();
  }

  Future<void> checkFirstLogin(BuildContext context) async {
    String? firstLogin = await storage.read(key: "firstLogin");
    if (firstLogin == null) {
      await storage.write(key: "firstLogin", value: "false");
    } else if (firstLogin == "false") {
      Navigator.of(context).pushAndRemoveUntil(
          MaterialPageRoute(builder: (context) => WelcomePage()),
          (Route route) => false);
    }
  }

  Future<bool> loadUserIfRemembered(BuildContext context) async {
    String? remember = await storage.read(key: "remember");

    if (remember == null) {
      checkFirstLogin(context);
      return false;
    }

    if (remember == "guest") {
      state = AsyncValue.data(AuthState.loggedIn);
      currentUser = guestUser;
      read(loginProvider.notifier).setGuestLogin();
      Navigator.of(context).pushNamed(
        RouteManager.homePage,
      );
      return true;
    }

    String? username = await storage.read(key: "username");
    String? accessToken = await storage.read(key: "token");

    if (username == null || accessToken == null) {
      return false;
    }

    SnackBar authSnack = SnackBar(
      content: Text("Authenticating ..."),
      duration: Duration(minutes: 1),
    );
    ScaffoldMessenger.of(context).showSnackBar(authSnack);

    state = AsyncValue.data(AuthState.authenticating);
    try {
      currentUser = User(
        username: username,
        token: accessToken,
      );
      UserApiClient.getUserInfo(currentUser!);

      state = AsyncValue.data(AuthState.loggedIn);
      read(loginProvider.notifier).setUserLogin();
      Navigator.of(context).pushNamed(
        RouteManager.homePage,
      );
      ScaffoldMessenger.of(context).clearSnackBars();
    } catch (e) {}
    return true;
  }

  Future<void> rememberUser(String username, String token) async {
    await storage.write(
      key: "remember",
      value: "user",
    );
    await storage.write(
      key: "username",
      value: username,
    );
    await storage.write(
      key: "token",
      value: token,
    );
  }

  Future<void> forgetUser() async {
    await storage.delete(key: "remember");
    await storage.delete(key: "username");
    await storage.delete(key: "token");
  }

  /// Do a user type authentication.
  Future<void> userLogin(Map<String, String?> userCreds, bool rememberMe,
      BuildContext parentContext) async {
    state = AsyncValue.data(AuthState.authenticating);
    SnackBar authSnack = SnackBar(
      content: Text("Authenticating ..."),
      duration: Duration(minutes: 1),
    );
    ScaffoldMessenger.of(parentContext).showSnackBar(authSnack);
    try {
      User? authenticatedUser = await AuthApiClient.login(userCreds);
      if (authenticatedUser != null) {
        currentUser = authenticatedUser;
        if (rememberMe) {
          rememberUser(currentUser!.username!, currentUser!.token!);
        }
        await UserApiClient.getUserInfo(currentUser!);

        state = AsyncValue.data(AuthState.loggedIn);
        read(loginProvider.notifier).setUserLogin();
        ScaffoldMessenger.of(parentContext).clearSnackBars();
        Navigator.of(parentContext).pushReplacementNamed(
          RouteManager.homePage,
        );
      } else {
        ScaffoldMessenger.of(parentContext).clearSnackBars();
        SnackBar errorSnack = SnackBar(
          content: Text("There was some error, please try again!"),
        );
        ScaffoldMessenger.of(parentContext).showSnackBar(errorSnack);
      }
    } catch (e) {}
  }

  /// Do a logout for both guest and user type authentications.
  Future<void> logout() async {
    LoginType loginType = read(loginProvider.notifier).loginType;
    if (loginType == LoginType.guest) {
      state = AsyncValue.data(AuthState.loggedOut);
      read(loginProvider.notifier).logout();
      currentUser = null;
    } else if (loginType == LoginType.user) {
      if (await AuthApiClient.logout()) {
        state = AsyncValue.data(AuthState.loggedOut);
        read(loginProvider.notifier).logout();
        currentUser = null;
      }
    }
  }

  Future<void> signup() async {}
}
