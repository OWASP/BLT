import 'package:flutter/material.dart';
import '../../pages/welcome.dart';
import 'components/onboard_page.dart';
import 'package:smooth_page_indicator/smooth_page_indicator.dart';
import 'data/onboard_page_data.dart';
import 'models/onboard_page_model.dart';

class Onboarding extends StatefulWidget {
  final Map<String, String> stats;

  const Onboarding({Key? key, required this.stats}) : super(key: key);
  @override
  State<Onboarding> createState() => _OnboardingState();
}

class _OnboardingState extends State<Onboarding> {
  final PageController pageController = PageController();
  late OnboardPageModel pageModel;

  @override
  void initState() {
    super.initState();
    onboardData[2].description = '${widget.stats["bugs"]} Bugs\n${widget.stats["users"]} Users\n${widget.stats["hunts"]} Hunts\n${widget.stats["domains"]} Domains';
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onPanUpdate: (details) {
        // Swiping in right direction.
        if (details.delta.dx > 0) {
          pageModel = onboardData[pageController.page?.round() ?? 0];
          _previousPage();
        }

        // Swiping in left direction.
        if (details.delta.dx < 0) {
          pageModel = onboardData[pageController.page?.round() ?? 0];
          if (pageController.page?.round() == 2) {
            Navigator.of(context).pushAndRemoveUntil(
              MaterialPageRoute(
                builder: (context) => WelcomePage(),
              ),
              (Route<dynamic> route) => false,
            );
          } else {
            _nextPage();
          }
        }
      },
      child: Stack(
        children: <Widget>[
          PageView.builder(
            controller: pageController,
            physics: NeverScrollableScrollPhysics(),
            itemCount: onboardData.length,
            itemBuilder: (context, index) {
              return OnboardPage(
                pageController: pageController,
                pageModel: onboardData[index],
                key: Key(''),
              );
            },
          ),
          Container(
            width: double.infinity,
            height: 100,
            child: Align(
              alignment: Alignment.bottomCenter,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                crossAxisAlignment: CrossAxisAlignment.baseline,
                textBaseline: TextBaseline.alphabetic,
                children: <Widget>[
                  Padding(
                    padding: const EdgeInsets.only(left: 20.0),
                    child: Text(
                      'Explore BugHeist',
                      style: TextStyle(
                        fontSize: 22,
                        fontWeight: FontWeight.bold,
                        color: Color(0xff305067),
                      ),
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.only(right: 32.0),
                    child: ElevatedButton(
                      onPressed: () {
                        Navigator.of(context).pushAndRemoveUntil(
                          MaterialPageRoute(
                            builder: (context) => WelcomePage(),
                          ),
                          (Route<dynamic> route) => false,
                        );
                      },
                      style: ElevatedButton.styleFrom(
                        elevation: 0,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(14.0),
                        ),
                        backgroundColor: Color(0xff305067),
                      ),
                      child: Text(
                        'Skip',
                        style: TextStyle(
                          fontSize: 18,
                          color: Colors.white,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
          Align(
            alignment: Alignment.bottomLeft,
            child: Padding(
              padding: const EdgeInsets.only(bottom: 60.0, left: 40),
              child: SmoothPageIndicator(
                controller: pageController,
                count: 3,
                effect: WormEffect(
                  dotColor: Color(0xff305067),
                  activeDotColor: Color(0xff305067),
                  dotHeight: 16,
                  dotWidth: 16,
                  type: WormType.normal,
                  // strokeWidth: 5,
                ),
              ),
            ),
          )
        ],
      ),
    );
  }

  _nextPage() {
    pageController.nextPage(
      duration: Duration(
        milliseconds: 1500,
      ),
      curve: Curves.easeInOutCubicEmphasized,
    );
  }

  _previousPage() {
    pageController.previousPage(
      duration: Duration(
        milliseconds: 1500,
      ),
      curve: Curves.easeInOutCubicEmphasized,
    );
  }
}
