import 'package:bugheist/pages/login.dart';
import 'package:bugheist/pages/login_signup.dart';
import 'package:bugheist/pages/profile.dart';
import 'package:bugheist/pages/signup.dart';
import 'package:flutter/material.dart';

class RouteManager {
  static const String profilePage = "/profile";
  static const String loginSignupPage = "/loginSignup";
  static const String loginPage = "/login";
  static const String signupPage = "/signup";
  static String currentRoute = "/loginSignup";
  static Route<dynamic> generateRoute(RouteSettings settings) {
    final arguments = settings.arguments;
    switch (settings.name) {
      case profilePage:
        return PageRouteBuilder(
          pageBuilder: (context, animation, secondaryAnimation) =>
              const UserProfile(),
          transitionsBuilder: (context, animation, secondaryAnimation, child) {
            const begin = Offset(-1.0, 0);
            const end = Offset.zero;
            const curve = Curves.ease;

            var tween =
                Tween(begin: begin, end: end).chain(CurveTween(curve: curve));

            return SlideTransition(
              position: animation.drive(tween),
              child: child,
            );
          },
          transitionDuration: const Duration(milliseconds: 750),
        );
      case loginSignupPage:
        return PageRouteBuilder(
          pageBuilder: (context, animation, secondaryAnimation) =>
              const LoginSignUp(),
          transitionsBuilder: (context, animation, secondaryAnimation, child) {
            const begin = Offset(1.0, 0);
            const end = Offset.zero;
            const curve = Curves.ease;

            var tween =
                Tween(begin: begin, end: end).chain(CurveTween(curve: curve));

            return SlideTransition(
              position: animation.drive(tween),
              child: child,
            );
          },
          transitionDuration: const Duration(milliseconds: 750),
        );
      // case loginPage:
      //   return PageRouteBuilder(
      //     pageBuilder: (context, animation, secondaryAnimation) => Login(),
      //     transitionsBuilder: (context, animation, secondaryAnimation, child) {
      //       const begin = Offset(-1.0, 0);
      //       const end = Offset.zero;
      //       const curve = Curves.ease;

      //       var tween =
      //           Tween(begin: begin, end: end).chain(CurveTween(curve: curve));

      //       return SlideTransition(
      //         position: animation.drive(tween),
      //         child: child,
      //       );
      //     },
      //     transitionDuration: const Duration(milliseconds: 750),
      //   );
      // case signupPage:
      //   return PageRouteBuilder(
      //     pageBuilder: (context, animation, secondaryAnimation) => Register(),
      //     transitionsBuilder: (context, animation, secondaryAnimation, child) {
      //       const begin = Offset(-1.0, 0);
      //       const end = Offset.zero;
      //       const curve = Curves.ease;

      //       var tween =
      //           Tween(begin: begin, end: end).chain(CurveTween(curve: curve));

      //       return SlideTransition(
      //         position: animation.drive(tween),
      //         child: child,
      //       );
      //     },
      //     transitionDuration: const Duration(milliseconds: 750),
      //   );

      default:
        return PageRouteBuilder(
          pageBuilder: (context, animation, secondaryAnimation) =>
              UserProfile(),
        );
    }
  }

  static void navigateToProfile(BuildContext context) {
    Navigator.of(context).pushNamed(RouteManager.profilePage);
    RouteManager.currentRoute = RouteManager.profilePage;
  }

  static void navigateToLoginSignUp(BuildContext context) {
    Navigator.of(context).pushNamed(RouteManager.loginSignupPage);
    RouteManager.currentRoute = RouteManager.loginSignupPage;
  }

  // static void navigateToLogin(BuildContext context) {
  //   Navigator.of(context).pushNamed(RouteManager.loginPage);
  //   RouteManager.currentRoute = RouteManager.loginPage;
  // }

  // static void navigateToSignup(BuildContext context) {
  //   Navigator.of(context).pushNamed(RouteManager.signupPage);
  //   RouteManager.currentRoute = RouteManager.signupPage;
  // }
}
