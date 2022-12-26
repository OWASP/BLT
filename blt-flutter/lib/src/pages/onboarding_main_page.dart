import 'package:flutter/material.dart';
import '../components/onboarding/onboarding.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:bugheist/src/providers/authstate_provider.dart';

class OnboardingMainPage extends ConsumerStatefulWidget {
  @override
  ConsumerState<OnboardingMainPage> createState() => _OnboardingMainPageState();
}

class _OnboardingMainPageState extends ConsumerState<OnboardingMainPage> {

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      await ref.read(authStateNotifier.notifier).loadUserIfRemembered(context);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Onboarding(),
    );
  }
}
