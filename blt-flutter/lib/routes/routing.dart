// import 'package:bugheist/pages/login.dart';
import 'package:bugheist/models/issue_model.dart';
import 'package:bugheist/pages/auth/forgot.dart';
import 'package:bugheist/pages/auth/signup.dart';
import 'package:bugheist/pages/error.dart';
import 'package:bugheist/pages/home/home.dart';
import 'package:bugheist/pages/legal.dart';
import 'package:bugheist/pages/auth/login.dart';
import 'package:bugheist/pages/profile.dart';
// import 'package:bugheist/pages/signup.dart';
import 'package:flutter/material.dart';

import '../pages/referral.dart';
import '../pages/welcome.dart';
import '../pages/about.dart';
import '../pages/leaderboards/company_scoreboard.dart';
import '../pages/leaderboards/global_leaderboard.dart';
import '../pages/issues/issue_detail.dart';
import '../pages/leaderboards/monthly_leaderboard.dart';

class RouteManager {
  static const String profilePage = "/profile";
  static const String welcomePage = "/loginSignup";
  static const String loginPage = "/login";
  static const String signupPage = "/signup";
  static const String forgotPage = "/forgot";
  static const String homePage = "/home";
  static String currentRoute = "/loginSignup";
  static const String legalPage = "/legal";
  static const String aboutPage = "/about";
  static const String referralPage = "/refer";
  static const String globalLeaderboardPage = "/globalBoard";
  static const String monthlyLeaderboardPage = "/monthlyBoard";
  static const String companyScoreboardPage = "/companyBoard";
  static const String issueDetailPage = "/issueDetail";

  static Route<dynamic> generateRoute(RouteSettings settings) {
    final arguments = settings.arguments;
    switch (settings.name) {
      case homePage:
        return PageRouteBuilder(
          pageBuilder: (context, animation, secondaryAnimation) => Home(
            startingIndex: arguments as int?,
          ),
          transitionsBuilder: (context, animation, secondaryAnimation, child) {
            const begin = 0.0;
            const end = 1.0;
            const curve = Curves.ease;

            var tween =
                Tween(begin: begin, end: end).chain(CurveTween(curve: curve));

            return FadeTransition(
              opacity: animation.drive(tween),
              child: child,
            );
          },
          transitionDuration: const Duration(milliseconds: 750),
        );

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
      case welcomePage:
        return PageRouteBuilder(
          pageBuilder: (context, animation, secondaryAnimation) =>
              const WelcomePage(),
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
      case forgotPage:
        return PageRouteBuilder(
          pageBuilder: (context, animation, secondaryAnimation) =>
              const ForgotPasswordPage(),
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

      case legalPage:
        return PageRouteBuilder(
          pageBuilder: (context, animation, secondaryAnimation) =>
              const LegalPage(),
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
      case aboutPage:
        return PageRouteBuilder(
          pageBuilder: (context, animation, secondaryAnimation) =>
              const AboutPage(),
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
          transitionDuration: const Duration(milliseconds: 500),
        );
      case referralPage:
        return PageRouteBuilder(
          pageBuilder: (context, animation, secondaryAnimation) =>
              const ReferralPage(),
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
          transitionDuration: const Duration(milliseconds: 500),
        );

      case issueDetailPage:
        return PageRouteBuilder(
          pageBuilder: (context, animation, secondaryAnimation) =>
              IssueDetailPage(
            issue: arguments as Issue,
          ),
          transitionsBuilder: (context, animation, secondaryAnimation, child) {
            const begin = Offset(0.0, 1.0);
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

      case globalLeaderboardPage:
        return PageRouteBuilder(
          pageBuilder: (context, animation, secondaryAnimation) =>
              const GlobalLeaderBoardPage(),
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
      case monthlyLeaderboardPage:
        return PageRouteBuilder(
          pageBuilder: (context, animation, secondaryAnimation) =>
              const MonthlyLeaderBoardPage(),
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
      case companyScoreboardPage:
        return PageRouteBuilder(
          pageBuilder: (context, animation, secondaryAnimation) =>
              const CompanyScoreBoardPage(),
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

      case loginPage:
        return PageRouteBuilder(
          pageBuilder: (context, animation, secondaryAnimation) => LoginPage(),
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
      case signupPage:
        return PageRouteBuilder(
          pageBuilder: (context, animation, secondaryAnimation) => SignUpPage(),
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

      default:
        return PageRouteBuilder(
          pageBuilder: (context, animation, secondaryAnimation) => ErrorPage(),
        );
    }
  }

  static void navigateToProfile(BuildContext context) {
    Navigator.of(context).pushNamed(RouteManager.profilePage);
    RouteManager.currentRoute = RouteManager.profilePage;
  }

  static void navigateToLoginSignUp(BuildContext context) {
    Navigator.of(context).pushNamed(RouteManager.welcomePage);
    RouteManager.currentRoute = RouteManager.welcomePage;
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
