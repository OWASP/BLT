import 'package:blt/src/pages/pages_import.dart';

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
      if (!mounted) {
        return;
      }
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
