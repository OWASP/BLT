import 'package:flutter/material.dart';

import '../models/onboard_page_model.dart';

List<OnboardPageModel> onboardData = [
  OnboardPageModel(
    Color(0xFFDC4654),
    Colors.white,
    Color(0xFFFFE074),
    0,
    'assets/logo_white.svg',
    'INSIGHT',
    'BLT',
    'BLT is a bug-hunting & logging tool which allows you, the user or company to hunt for bugs, claim bug hounties and allow you to start bughunting spree/contest respectively.',
  ),
  OnboardPageModel(
    Colors.white,
    Color(0xFFDC4654),
    Color(0xFFE6E6E6),
    1,
    'assets/blt_logo.svg',
    'EARN',
    'POINTS',
    '(+1) Invite friends\n(+2) Verify other bug reports\n(+3) Fix issues on websites, apps or hardware\n(+4) Find a bug on a new site or app',
  ),
  OnboardPageModel(
    Color(0xFFDC4654),
    Colors.white,
    Color(0xFFE6E6E6),
    2,
    'assets/logo_white.svg',
    'CURRENT',
    'STATISTICS',
    '1200+ Bugs\n790+ Users\n3 Hunts\n590+ Domains',
  ),
];
