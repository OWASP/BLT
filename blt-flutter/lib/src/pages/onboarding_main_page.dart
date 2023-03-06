import 'package:flutter/material.dart';
import '../components/onboarding/onboarding.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:blt/src/providers/authstate_provider.dart';

import '../util/api/general_api.dart';

class OnboardingMainPage extends ConsumerStatefulWidget {
  @override
  ConsumerState<OnboardingMainPage> createState() => _OnboardingMainPageState();
}

class _OnboardingMainPageState extends ConsumerState<OnboardingMainPage> {
  Map<String, String> stats = {};

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      await ref.read(authStateNotifier.notifier).loadUserIfRemembered(context);
      Map<String, String> new_stats = await GeneralApiClient.getStats();
      setState(() {
        stats = new_stats;
      });
    });
  }

  @override
  Widget build(BuildContext context) {
    if (stats["bugs"] != null) {
      return Scaffold(
        body: Onboarding(
          stats: stats,
        ),
      );
    } else {
      return Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }
  }
}
