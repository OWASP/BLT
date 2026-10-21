import 'package:blt/src/pages/drawer/drawer_imports.dart';
import 'package:blt/src/util/brand.dart';

class SponsorPage extends StatefulWidget {
  const SponsorPage({super.key});

  @override
  State<SponsorPage> createState() => _SponsorPageState();
}

class _SponsorPageState extends State<SponsorPage>
    with TickerProviderStateMixin {
  late AnimationController animationController;
  Map<String, dynamic>? intent;
  int selected = -1;

  final List<dynamic> tiers = [
    {
      "title": "Ant Tier",
      "svg": "assets/ant.svg",
      "subtitle": "Join the Colony - \$10",
      "option": 0,
    },
    {
      "title": "Flea Tier",
      "svg": "assets/flea.svg",
      "subtitle": "Leap into Action - \$50",
      "option": 2,
    },
    {
      "title": "Scorpion Tier",
      "svg": "assets/scorpion.svg",
      "subtitle": "Strike with Power - \$100",
      "option": 3,
    },
    {
      "title": "Wasp Tier",
      "svg": "assets/wasp.svg",
      "subtitle": "Rule the Hive - \$500",
      "option": 4,
    }
  ];

  @override
  void initState() {
    animationController =
        AnimationController(duration: new Duration(seconds: 2), vsync: this);
    animationController.repeat();
    super.initState();
  }

  @override
  void dispose() {
    animationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;
    // final Size size = MediaQuery.of(context).size;
    return Scaffold(
      backgroundColor: isDarkMode
          ? BLTColors.darkBackground
          : Theme.of(context).canvasColor,
      appBar: AppBar(
        backgroundColor:
            isDarkMode ? BLTColors.darkSurface : BLTColors.primary,
        leading: IconButton(
          icon: Icon(
            Icons.arrow_back_ios_new_rounded,
            color: Colors.white,
          ),
          onPressed: () {
            Navigator.of(context).pop();
          },
        ),
        title: Text(
          "Sponsor BLT",
          style: TextStyle(
            color: Colors.white,
            fontSize: 20,
          ),
        ),
      ),
      body: SingleChildScrollView(
        child: Padding(
          padding: EdgeInsets.symmetric(horizontal: 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                padding: EdgeInsets.fromLTRB(0, 12, 0, 12),
                child: Text(
                  "Sponsor BLT",
                  style: BLTFonts.system(
                    textStyle: TextStyle(
                      color: BLTColors.textMuted,
                      fontSize: 25,
                    ),
                  ),
                ),
              ),
              Container(
                padding: EdgeInsets.fromLTRB(0, 0, 0, 16),
                child: Text(
                  "Join us in driving innovation and excellence in the tech community. Your sponsorship helps fuel groundbreaking projects, ensuring we continue to develop and share cutting-edge solutions with the world.",
                  style: BLTFonts.system(
                    textStyle: TextStyle(
                      color: BLTColors.textMuted,
                    ),
                  ),
                ),
              ),
              SizedBox(height: 10),
              ListView.separated(
                physics: NeverScrollableScrollPhysics(),
                shrinkWrap: true,
                itemBuilder: (context, index) {
                  if (selected == index) {
                    return GestureDetector(
                      onTap: () {
                        setState(() {
                          selected = -1;
                        });
                      },
                      child: SelectedSponsorTile(sponsor: tiers[index]),
                    );
                  }
                  return GestureDetector(
                    onTap: () {
                      setState(() {
                        selected = index;
                      });
                    },
                    child: UnselectedSponsorTile(sponsor: tiers[index]),
                  );
                },
                separatorBuilder: (context, index) => SizedBox(height: 10),
                itemCount: tiers.length,
              ),
              SizedBox(height: 30),
              TextButton(
                child: Padding(
                  padding: const EdgeInsets.all(8.0),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(
                        Icons.volunteer_activism,
                        color: Colors.white,
                        size: 28,
                      ),
                      SizedBox(width: 5),
                      Text(
                        "Sponsor",
                        style: BLTFonts.system(
                          textStyle: TextStyle(
                            color: Colors.white,
                            fontSize: 22,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                style: ButtonStyle(
                  shape: WidgetStateProperty.all<RoundedRectangleBorder>(
                    RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8.0),
                    ),
                  ),
                  backgroundColor: WidgetStateProperty.all(
                    isDarkMode
                        ? BLTColors.primaryDark
                        : BLTColors.primary,
                  ),
                ),
                onPressed: () {
                  if (selected == -1) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text(
                          "Please choose a tier before proceeding to payment.",
                          style: TextStyle(color: Colors.white),
                        ),
                        backgroundColor: isDarkMode
                            ? BLTColors.primaryDark
                            : BLTColors.primary,
                      ),
                    );
                  } else {
                    Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (context) => OWASPDonationWebView(
                          selectedIndex: tiers[selected]["option"],
                        ),
                      ),
                    );
                  }
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class UnselectedSponsorTile extends StatelessWidget {
  const UnselectedSponsorTile({super.key, this.sponsor});
  final dynamic sponsor;

  @override
  Widget build(BuildContext context) {
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;
    final Size size = MediaQuery.of(context).size;
    return Container(
      width: size.width,
      decoration: BoxDecoration(
        // color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          width: 1.5,
          color: isDarkMode ? BLTColors.gray700 : BLTColors.primary,
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Container(
          width: size.width * 0.4,
          child: Row(
            children: [
              SizedBox(
                width: size.width * 0.12,
                height: size.width * 0.12,
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: SvgPicture.asset(
                    sponsor["svg"],
                    colorFilter: isDarkMode
                        ? ColorFilter.mode(
                            Color.fromARGB(255, 212, 212, 212), BlendMode.srcIn)
                        : null,
                  ),
                ),
              ),
              SizedBox(width: 10),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    sponsor["title"],
                    style: BLTFonts.system(
                      textStyle: TextStyle(
                        color: isDarkMode
                            ? Color.fromARGB(255, 161, 161, 161)
                            : Color.fromARGB(255, 88, 88, 88),
                        fontSize: 22,
                      ),
                    ),
                  ),
                  Text(
                    sponsor["subtitle"],
                    style: BLTFonts.system(
                      textStyle: TextStyle(
                        color: !isDarkMode
                            ? Color.fromARGB(255, 161, 161, 161)
                            : Color.fromARGB(255, 98, 98, 98),
                        fontSize: 16,
                      ),
                    ),
                  )
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class SelectedSponsorTile extends StatelessWidget {
  const SelectedSponsorTile({super.key, this.sponsor});
  final dynamic sponsor;

  @override
  Widget build(BuildContext context) {
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;
    final Size size = MediaQuery.of(context).size;
    return Container(
      width: size.width,
      decoration: BoxDecoration(
        // color: Colors.white,
        color: isDarkMode ? BLTColors.darkSurface : BLTColors.primary,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Container(
              // width: size.width * 0.5,
              child: Row(
                children: [
                  SizedBox(
                    width: size.width * 0.12,
                    height: size.width * 0.12,
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(12),
                      child: SvgPicture.asset(
                        sponsor["svg"],
                        colorFilter: isDarkMode
                            ? ColorFilter.mode(Colors.white, BlendMode.srcIn)
                            : null,
                      ),
                    ),
                  ),
                  SizedBox(width: 10),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        sponsor["title"],
                        style: BLTFonts.system(
                          textStyle: TextStyle(
                            // color: !isDarkMode
                            //     ? Color.fromARGB(255, 161, 161, 161)
                            //     : BLTColors.textMuted,
                            color: Colors.white,
                            fontSize: 22,
                          ),
                        ),
                      ),
                      Text(
                        sponsor["subtitle"],
                        style: BLTFonts.system(
                          textStyle: TextStyle(
                            color: const Color.fromARGB(255, 233, 232, 232),
                            // color: !isDarkMode
                            //     ? Color.fromARGB(255, 161, 161, 161)
                            //     : BLTColors.textMuted,
                            fontSize: 16,
                          ),
                        ),
                      )
                    ],
                  ),
                ],
              ),
            ),
            Icon(
              Icons.verified,
              color: isDarkMode
                  ? Color.fromARGB(255, 161, 161, 161)
                  : Colors.white,
              size: 30,
            )
          ],
        ),
      ),
    );
  }
}
