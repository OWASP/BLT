import 'package:blt/src/components/components_import.dart';
import 'package:blt/src/util/brand.dart';

List<OnboardPageModel> onboardData = [
  OnboardPageModel(
    BLTColors.primary,
    Colors.white,
    Color(0xFFFFE074),
    0,
    'assets/blt_wasp_white.svg',
    'INSIGHT',
    'BLT',
    'BLT is a bug-hunting & logging tool which allows you, the user or company to hunt for bugs, claim bug hounties and allow you to start bughunting spree/contest respectively.',
  ),
  OnboardPageModel(
    Colors.white,
    BLTColors.primary,
    BLTColors.gray200,
    1,
    'assets/blt_wasp.svg',
    'EARN',
    'POINTS',
    '(+1) Invite friends\n(+2) Verify other bug reports\n(+3) Fix issues on websites, apps or hardware\n(+4) Find a bug on a new site or app',
  ),
  OnboardPageModel(
    BLTColors.primary,
    Colors.white,
    BLTColors.gray200,
    2,
    'assets/blt_wasp_white.svg',
    'CURRENT',
    'STATISTICS',
    '1200+ Bugs\n790+ Users\n3 Hunts\n590+ Domains',
  ),
];
