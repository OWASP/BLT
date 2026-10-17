//import 'dart:async';

import 'package:blt/src/pages/onboarding_main_page.dart';
import 'package:blt/src/providers/dark_mode_provider.dart';
import 'package:blt/src/providers/language_provider.dart';
import 'package:blt/src/routes/routing.dart';
import 'package:blt/src/util/theme_data.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_gen/gen_l10n/app_localizations.dart';
//import 'package:receive_sharing_intent/receive_sharing_intent.dart';

/// ### The BLT app's root widget
class BLT extends StatefulWidget {
  const BLT({Key? key}) : super(key: key);

  @override
  BLTState createState() => BLTState();
}

class BLTState extends State<BLT> {
  final _messengerKey = GlobalKey<ScaffoldMessengerState>();

  @override
  Widget build(BuildContext context) {
    return ProviderScope(
      child: GestureDetector(
        onTap: () {
          FocusScopeNode currentScope = FocusScope.of(context);
          if (!currentScope.hasPrimaryFocus && currentScope.hasFocus) {
            FocusManager.instance.primaryFocus!.unfocus();
          }
        },
        child: Consumer(
          builder: (context, ref, _) {
            final currentLanguage = ref.watch(languageProvider);
            final themeMode = ref.watch(darkModeProvider);

            return MaterialApp(
              localizationsDelegates: [
                AppLocalizations.delegate,
                GlobalMaterialLocalizations.delegate,
                GlobalWidgetsLocalizations.delegate,
                GlobalCupertinoLocalizations.delegate,
              ],
              supportedLocales: AppLocalizations.supportedLocales,
              locale: Locale(currentLanguage),
              scaffoldMessengerKey: _messengerKey,
              debugShowCheckedModeBanner: false,
              onGenerateRoute: RouteManager.generateRoute,
              title: 'BLT',
              theme: AppTheme.lightTheme,
              darkTheme: AppTheme.darkTheme,
              themeMode:
                  themeMode.isDarkMode ? ThemeMode.dark : ThemeMode.light,
              home: Scaffold(body: OnboardingMainPage()),
            );
          },
        ),
      ),
    );
  }
}
